from app.core.redis_client import get_redis_client
import asyncio
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

async def test_get_redis():
    """
    Test the get_redis dependency function.

    Args:
        redis (Redis): The Redis client instance provided by the dependency.

    Asserts:
        - The Redis client instance is not None.
        - The Redis client instance is of type Redis.
    """
    redis_client = get_redis_client()
    result = await redis_client.ping()
    print(f"Redis ping result: {result}")
    await redis_client.set("name2", "israel-s")
    await redis_client.aclose()  # Close the Redis connection after the test


asyncio.run(test_get_redis())