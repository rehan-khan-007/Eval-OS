import os
import pickle
import hashlib
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
redis_client = redis.from_url(REDIS_URL, decode_responses=False)

# Prefix all keys so EvalOS doesn't collide with AgentOS in the shared Redis
KEY_PREFIX = "evalos:"

def generate_cache_key(*args) -> str:
    """Generates a consistent SHA256 hash key from the provided arguments."""
    key_string = "|".join(str(arg) for arg in args)
    hashed_key = hashlib.sha256(key_string.encode()).hexdigest()
    return f"{KEY_PREFIX}{hashed_key}"

async def get_cached(key: str):
    """Fetches a value from Redis and deserializes it."""
    cached_data = await redis_client.get(key)
    if cached_data:
        return pickle.loads(cached_data)
    return None

async def set_cached(key: str, value, ttl: int = 86400):
    """Serializes a value and saves it to Redis with a TTL (default 24 hours)."""
    pickled_value = pickle.dumps(value)
    await redis_client.setex(key, ttl, pickled_value)
