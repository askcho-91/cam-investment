from app.modules.auth.services import create_user as auth_create_user
from app.core.models import User
from app.modules.users.schemas import CreateUserSchema, UpdateUserSchema
from app.core.dependencies import db_dependency


async def create_user(user_data: CreateUserSchema, db: db_dependency):
    """Creates a new user in the database and authentication system."""
    # Create user in the authentication system
    auth_user_id = None
    try:
        auth_user = await auth_create_user(email=user_data.email, password=user_data.password)

        if not auth_user:
            raise Exception("Failed to create user")
        auth_user_id = auth_user.id
    

        # Create user in the database
        new_user = User(
            email=user_data.email,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            auth_id=auth_user_id
        )

        db.add(new_user)
        await db.commit()

        await db.refresh(new_user)

        return new_user
    except Exception as e:
            raise Exception(f"{str(e)}")


