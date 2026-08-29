from fastapi import APIRouter
from app.modules.auth.services import login_user
from app.modules.auth.schemas import LoginSchema
from app.core.dependencies import db_dependency,  current_user_dependency, authorization_header

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post("/login")
def login(login_data: LoginSchema, passwordless: bool = False):
    """
    Logs in a user using the Supabase client.
    """
    return login_user(passwordless, login_data.email, login_data.password)


@auth_router.get("/me")
async def get_current_user(current_user: current_user_dependency, authorization: authorization_header):
    """
    Retrieves the current authenticated user.
    """
    return current_user
