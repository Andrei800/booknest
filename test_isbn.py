import asyncio
import httpx

async def test():
    isbn = "9780141439518"  # Pride and Prejudice
    
    print(f"Testing ISBN: {isbn}")
    print("-" * 50)
    
    # Test Google Books
    print("Testing Google Books API...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={"q": f"isbn:{isbn}", "maxResults": 1}
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Total items: {data.get('totalItems', 0)}")
        if data.get('items'):
            item = data['items'][0]
            volume_info = item.get('volumeInfo', {})
            print(f"Title: {volume_info.get('title')}")
            print(f"Authors: {volume_info.get('authors')}")
        else:
            print("No items found")
    
    print("-" * 50)
    
    # Test Open Library
    print("Testing Open Library API...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"https://openlibrary.org/isbn/{isbn}.json"
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Title: {data.get('title')}")
        else:
            print("Not found")

asyncio.run(test())
