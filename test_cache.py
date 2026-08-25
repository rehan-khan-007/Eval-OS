import asyncio
import os
from dotenv import load_dotenv
from cache import generate_cache_key, get_cached, set_cached

load_dotenv()

async def test_redis():
    redis_url = os.getenv("REDIS_URL")
    print(f"REDIS_URL loaded: {redis_url is not None}")
    if redis_url:
        print(f"URL starts with: {redis_url[:15]}...")

    test_key = generate_cache_key("test", "connection")
    print(f"Generated test key: {test_key}")

    print("Attempting to set cache...")
    await set_cached(test_key, {"message": "hello from evalos"})
    
    print("Attempting to get cache...")
    result = await get_cached(test_key)
    
    if result and result.get("message") == "hello from evalos":
        print("\nSUCCESS: Redis cache is working perfectly!")
    else:
        print("\nFAILED: Could not read from Redis cache. Check your REDIS_URL.")

if __name__ == "__main__":
    asyncio.run(test_redis())
