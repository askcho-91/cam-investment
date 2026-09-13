from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import (
    current_user_dependency,
    db_dependency,
    redis_dependency,
)
from .services import create_user, update_user
from .schemas import CreateUserSchema, UpdateUserSchema, UserResponse

user_router = APIRouter(prefix="/users", tags=["Users"])


@user_router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_new_user(user: CreateUserSchema, db: db_dependency):
    """
    Endpoint to create a new user.

    Args:
        user (CreateUserSchema): The user data to create a new user.
        db (AsyncSession): The database session dependency.

    Returns:
        User: The newly created user object.
    """
    return await create_user(user_data=user, db=db)


@user_router.get("/me", response_model=UserResponse)
async def get_current_user_profile(user: current_user_dependency):
    return user


@user_router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    data: UpdateUserSchema,
    user: current_user_dependency,
    db: db_dependency,
    redis: redis_dependency,
):
    try:
        updated_user = await update_user(user, data, db)
        await redis.delete(f"user:{updated_user.auth_user_id}")
        return updated_user
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


# @user_router.get("/{user_id}")
# async def get_user(user_id: int, db: db_dependency):
