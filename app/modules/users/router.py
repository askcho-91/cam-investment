from fastapi import APIRouter
from app.core.dependencies import current_user_dependency, db_dependency
from .services import create_user
from .schemas import CreateUserSchema

user_router = APIRouter(prefix="/users", tags=["Users"])


@user_router.post("/")
async def create_new_user(user: CreateUserSchema, db: db_dependency):
    """
    Endpoint to create a new user.

    Args:
        user (CreateUserSchema): The user data to create a new user.
        db (AsyncSession): The database session dependency.

    Returns:
        User: The newly created user object.
    """
    try:
        new_user = await create_user(user_data=user, db=db)
        return new_user
    except Exception as e:
        return {"error": f"An error occurred while creating the user: {str(e)}"}


# @user_router.get("/{user_id}")
# async def get_user(user_id: int, db: db_dependency):
