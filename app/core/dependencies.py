from .redis_client import get_redis_client
from redis.asyncio import Redis
from fastapi import Depends, Request, HTTPException
from fastapi.security import HTTPBearer
from typing import Annotated
from .auth import verify_auth_jwt
from .models import User
from sqlalchemy import select
from json import loads, dumps

security = HTTPBearer()

from .db_config import async_session
from sqlalchemy.ext.asyncio import AsyncSession

async def get_redis() -> Redis:
    """
    Dependency function to get a Redis client instance.

    Returns:
        Redis: An instance of the Redis client.
    """
    return get_redis_client()


async def get_db() -> AsyncSession:
    """
    Dependency function to get a database session for FastAPI routes. It creates an asynchronous session and ensures that it is properly closed after use.

    Yields:
        AsyncSession: An asynchronous database session for use in route handlers.
    """
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()



async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db), redis: Redis = Depends(get_redis)
) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = auth_header.split(" ")[1]

    try:
        payload = verify_auth_jwt(token)
        auth_user_id = payload["sub"]
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    cached_user = await redis.get(f"user:{auth_user_id}")  

    if cached_user:
        return User(**loads(cached_user))

    curent_user = await db.execute(select(User).where(User.auth_user_id == auth_user_id))
    user = curent_user.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await redis.setex(f"user:{auth_user_id}", 3600, dumps(user.json_data()))  # Cache for 1 hour

    return user


redis_dependency = Annotated[Redis, Depends(get_redis)]
db_dependency = Annotated[AsyncSession, Depends(get_db)]
current_user_dependency = Annotated[User, Depends(get_current_user)]
authorization_header = Annotated[str, Depends(security)]