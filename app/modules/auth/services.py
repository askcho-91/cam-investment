from .auth_setup import Auth
from gotrue import User
from fastapi import HTTPException, status

auth = Auth()



def login_user(passwordless : bool = False, email : str = None, password : str | None = None):
    """Logs in a user using the Supabase client."""
    try:
        if passwordless:
            response = auth.passwordless_login(email=email)
            return response
        else:
            response = auth.login_user(email=email, password=password)
            return response
    except Exception as e:
        raise Exception(f"Failed to login user: {str(e)}")


async def create_user(email: str, password: str) -> User:
    """Creates a new user using the Supabase client."""
    try:
        response = auth.create_user(email=email, password=password)
        return response
    except Exception as e:
        raise Exception(f"{str(e)}")

def refresh_token(refresh_token: str) -> User:
    """Refreshes the user's authentication token using the Auth service."""
    try:
        response = auth.refresh_token(refresh_token)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to refresh token: {str(e)}",
        )

