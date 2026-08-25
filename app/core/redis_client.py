from redis.asyncio import Redis
from functools import lru_cache
from os import getenv

REDIS_URL = getenv("REDIS_URL", "")

@lru_cache()
def get_redis_client() -> Redis:
    """
    Get a Redis client instance.

    Returns:
        Redis: An instance of the Redis client.
    """
    return Redis.from_url(
     url=REDIS_URL
    )