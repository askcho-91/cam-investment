from .redis_client import get_redis_client
from redis.asyncio import Redis
from fastapi import Depends
from typing import Annotated

async def get_redis() -> Redis:
    """
    Dependency function to get a Redis client instance.

    Returns:
        Redis: An instance of the Redis client.
    """
    return get_redis_client()

redis_dependency = Annotated[Redis, Depends(get_redis)]