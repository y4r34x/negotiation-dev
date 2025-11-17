import asyncio
import httpx
import json

async def test_api():
    url = "https://bsky-search-proxy.tech/search?q=python&limit=2"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url)
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            data = response.json()
            print(f"Response type: {type(data)}")
            print(f"Response (first 1000 chars): {json.dumps(data, indent=2)[:1000]}")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api())

