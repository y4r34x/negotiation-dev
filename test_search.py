import asyncio
import httpx
import json
from main import rewrite_search_query, search_term

async def test_search():
    # Test the rewrite function
    test_terms = [
        "abortion direction good",
        "gas prices high",
        "python"
    ]
    
    for term in test_terms:
        rewritten = rewrite_search_query(term)
        print(f"Original: '{term}' -> Rewritten: {rewritten}")
    
    # Test actual search
    print("\nTesting actual search...")
    result = await search_term("python")
    print(f"Search result for 'python': {result}")

if __name__ == "__main__":
    asyncio.run(test_search())

