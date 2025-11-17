import asyncio
import httpx
import json
import os

async def test_authenticated():
    """Test the authenticated Bluesky API endpoint"""
    handle = os.getenv("BLUESKY_HANDLE")
    password = os.getenv("BLUESKY_PASSWORD") or os.getenv("BLUESKY_APP_PASSWORD")
    
    if not handle or not password:
        print("ERROR: BLUESKY_HANDLE and BLUESKY_PASSWORD must be set")
        return
    
    session_url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    search_url = "https://bsky.social/xrpc/app.bsky.feed.searchPosts"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Create session
            print("Creating session...")
            session_response = await client.post(
                session_url,
                json={"identifier": handle, "password": password},
            )
            print(f"Session status: {session_response.status_code}")
            
            if session_response.status_code != 200:
                print(f"Session error: {session_response.text}")
                return
            
            session_data = session_response.json()
            access_token = session_data.get("accessJwt")
            
            if not access_token:
                print("ERROR: No access token received")
                return
            
            print("Session created successfully")
            
            # Test search
            print("\nTesting search...")
            headers = {"Authorization": f"Bearer {access_token}"}
            search_response = await client.get(
                search_url,
                params={"q": "python", "limit": 2},
                headers=headers,
            )
            
            print(f"Search status: {search_response.status_code}")
            
            if search_response.status_code == 200:
                data = search_response.json()
                print(f"\nResponse keys: {list(data.keys())}")
                if "posts" in data:
                    print(f"Found {len(data['posts'])} posts")
                    if data['posts']:
                        print(f"\nFirst post keys: {list(data['posts'][0].keys())}")
                        print(f"\nFirst post indexedAt: {data['posts'][0].get('indexedAt')}")
            else:
                print(f"Search error: {search_response.text[:500]}")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_authenticated())

