import asyncio
import httpx
import json

async def test_bluesky_api():
    """Test the official Bluesky API endpoint to see the response format"""
    url = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params={"q": "python", "limit": 2})
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\nResponse keys: {list(data.keys())}")
                print(f"\nFull response (first 2000 chars):")
                print(json.dumps(data, indent=2)[:2000])
                
                # Check for posts
                if "posts" in data:
                    print(f"\nFound {len(data['posts'])} posts")
                    if data['posts']:
                        print(f"\nFirst post keys: {list(data['posts'][0].keys())}")
                        print(f"\nFirst post sample:")
                        print(json.dumps(data['posts'][0], indent=2)[:1000])
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bluesky_api())

