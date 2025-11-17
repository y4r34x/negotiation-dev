import ast
import asyncio
import io
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import httpx
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SEARCH_PAGE_LIMIT = 100
RECENT_DAYS = 7
BLUESKY_PUBLIC_HOST = os.getenv("BLUESKY_PUBLIC_HOST", "https://public.api.bsky.app")
BLUESKY_AUTH_HOST = os.getenv("BLUESKY_AUTH_HOST", "https://bsky.social")
BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.getenv("BLUESKY_APP_PASSWORD") or os.getenv("BLUESKY_PASSWORD")
BLUESKY_PUBLIC_SEARCH_URL = f"{BLUESKY_PUBLIC_HOST.rstrip('/')}/xrpc/app.bsky.feed.searchPosts"
BLUESKY_AUTH_SEARCH_URL = f"{BLUESKY_AUTH_HOST.rstrip('/')}/xrpc/app.bsky.feed.searchPosts"
BLUESKY_SESSION_URL = f"{BLUESKY_AUTH_HOST.rstrip('/')}/xrpc/com.atproto.server.createSession"
_SESSION_LOCK = asyncio.Lock()
_SESSION_STATE: Dict[str, Optional[str]] = {"access": None, "refresh": None}


def rewrite_search_query(term: str) -> str:
    if not term:
        return ""
    sanitized = term.replace('"', "").strip()
    return " ".join(sanitized.split())


async def _ensure_bluesky_session(client: httpx.AsyncClient, *, force: bool = False) -> str:
    if not BLUESKY_HANDLE or not BLUESKY_APP_PASSWORD:
        raise RuntimeError("Bluesky credentials are not configured")

    async with _SESSION_LOCK:
        if not force and _SESSION_STATE["access"]:
            return _SESSION_STATE["access"]  # type: ignore[return-value]

        response = await client.post(
            BLUESKY_SESSION_URL,
            json={"identifier": BLUESKY_HANDLE, "password": BLUESKY_APP_PASSWORD},
        )
        response.raise_for_status()
        data = response.json()

        access = data.get("accessJwt")
        refresh = data.get("refreshJwt")
        if not access:
            raise RuntimeError("Bluesky session response missing access token")

        _SESSION_STATE["access"] = access
        _SESSION_STATE["refresh"] = refresh
        return access


def _extract_posts(payload: dict) -> List[dict]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("posts"), list):
        return payload["posts"]
    if isinstance(payload.get("results"), list):
        return payload["results"]
    nested = payload.get("data")
    if isinstance(nested, dict):
        if isinstance(nested.get("posts"), list):
            return nested["posts"]
        if isinstance(nested.get("results"), list):
            return nested["results"]
    return []


async def _search_official_endpoint(
    client: httpx.AsyncClient,
    endpoint: str,
    query: str,
    *,
    authenticated: bool,
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)
    cursor: Optional[str] = None
    seen = set()
    total = 0
    headers: Dict[str, str] = {}
    max_pages = 10  # Limit pagination to prevent infinite loops

    if authenticated:
        try:
            token = await _ensure_bluesky_session(client, force=False)
            headers["Authorization"] = f"Bearer {token}"
        except Exception as e:
            logger.warning(f"Failed to authenticate: {e}")
            return 0

    refreshed = False
    page_count = 0

    while page_count < max_pages:
        params = {"q": query, "limit": SEARCH_PAGE_LIMIT}
        if cursor:
            params["cursor"] = cursor

        try:
            logger.info(f"Searching Bluesky: query='{query}', page={page_count + 1}, authenticated={authenticated}")
            response = await client.get(endpoint, params=params, headers=headers, timeout=10.0)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error_text = exc.response.text[:200] if hasattr(exc.response, 'text') else str(exc.response)
            logger.warning(f"HTTP error {status_code} for query '{query}': {error_text}")
            
            # Handle authentication errors
            if status_code in (401, 403):
                if authenticated and not refreshed:
                    try:
                        token = await _ensure_bluesky_session(client, force=True)
                        headers["Authorization"] = f"Bearer {token}"
                        refreshed = True
                        continue
                    except Exception as e:
                        logger.error(f"Failed to refresh session: {e}")
                # If not authenticated or already refreshed, return 0
                return total
            
            # For other HTTP errors, return what we have so far
            return total
        except httpx.TimeoutException:
            logger.warning(f"Timeout searching for '{query}'")
            return total
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            return total

        try:
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to parse JSON response for '{query}': {e}")
            return total

        posts = _extract_posts(data)
        logger.info(f"Found {len(posts)} posts for query '{query}' on page {page_count + 1}")

        if not posts:
            break

        for p in posts:
            uri = None
            if isinstance(p, dict):
                uri = p.get("uri") or p.get("post", {}).get("uri")
            if not uri or uri in seen:
                continue
            seen.add(uri)

            ts = None
            if isinstance(p, dict):
                # Bluesky API uses indexedAt at the post level
                ts = (
                    p.get("indexedAt")
                    or p.get("indexed_at")
                    or p.get("createdAt")
                    or p.get("record", {}).get("indexedAt")
                    or p.get("record", {}).get("createdAt")
                )
            if not ts:
                continue

            try:
                if isinstance(ts, (int, float)):
                    ts_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                else:
                    ts_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                    if ts_dt.tzinfo is None:
                        ts_dt = ts_dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue

            if ts_dt >= cutoff:
                total += 1

        cursor = data.get("cursor")
        if not cursor:
            break
        
        page_count += 1

    logger.info(f"Search complete for '{query}': {total} posts in last {RECENT_DAYS} days")
    return total


async def search_term(term: str) -> int:
    query = rewrite_search_query(term)
    if not query:
        return 0

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            # Try authenticated endpoint first if credentials are available
            if BLUESKY_HANDLE and BLUESKY_APP_PASSWORD:
                logger.info(f"Using authenticated search for '{query}'")
                count = await _search_official_endpoint(
                    client,
                    BLUESKY_AUTH_SEARCH_URL,
                    query,
                    authenticated=True,
                )
                if count > 0:
                    return count
            
            # Fallback to public endpoint (may require auth, but worth trying)
            logger.info(f"Trying public endpoint for '{query}'")
            count = await _search_official_endpoint(
                client,
                BLUESKY_PUBLIC_SEARCH_URL,
                query,
                authenticated=False,
            )
            return count
            
    except Exception as e:
        logger.error(f"Unexpected error searching for '{term}': {e}")
        return 0


@app.post("/process")
async def process_csv(file: UploadFile = File(...)):
    try:
        if not file.filename or not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="File must be a CSV")

        logger.info(f"Processing file: {file.filename}")
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        if "search_terms" not in df.columns:
            raise HTTPException(status_code=400, detail="Missing search_terms column")

        results = []
        total_rows = len(df)
        for row_number, (_, row) in enumerate(df.iterrows(), start=1):
            try:
                terms = ast.literal_eval(row["search_terms"])
                if not isinstance(terms, list):
                    raise ValueError()
            except Exception as e:
                logger.error(f"Row {row_number}: invalid search_terms - {e}")
                raise HTTPException(status_code=400, detail=f"Row {row_number}: invalid search_terms")

            logger.info(f"Processing row {row_number}/{total_rows} with {len(terms)} search terms")
            freqs = []
            for j, t in enumerate(terms):
                logger.info(f"  Searching term {j+1}/{len(terms)}: '{t}'")
                try:
                    freq = await search_term(str(t))
                    freqs.append(freq)
                    logger.info(f"    Result: {freq}")
                except Exception as e:
                    logger.error(f"    Error searching '{t}': {e}")
                    freqs.append(0)
            results.append(freqs)

        df["search_frequency"] = results

        out = io.StringIO()
        df.to_csv(out, index=False)
        out.seek(0)

        logger.info(f"Successfully processed {file.filename}")
        return StreamingResponse(
            io.BytesIO(out.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=processed_{file.filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/")
async def root():
    return {"message": "CSV Processing API running"}
