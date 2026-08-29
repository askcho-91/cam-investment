from supabase import create_client, Client
from gotrue.types import User
from os import getenv
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file


class Auth:
    """initializes the authentication"""

    def __init__(self):
        """Initializes the Auth instance by creating a Supabase client using the provided URL and key."""
        supabase_url = getenv("SUPABASE_URL")
        supabase_key = getenv("SUPABASE_KEY")
        supabase_service_key = getenv("SUPABASE_SERVICE_KEY")
        frontend_url = getenv("FRONTEND_URL", "app.manaja.solutions")

        self._client: Client = create_client(supabase_url, supabase_key)
        self.__service_client: Client = create_client(
            supabase_url, supabase_service_key
        )
        self._frontend_url = frontend_url.strip().rstrip("/")

    def generate_magic_link(self, email: str) -> str:
        """Build a one-click sign-in link for Resend templates (does not email via Supabase)."""
        try:
            response = self.__service_client.auth.admin.generate_link(
                {
                    "type": "magiclink",
                    "email": email,
                    "options": {
                        "redirect_to": "/login",
                    },
                }
            )
            return response
        except Exception as e:
            raise Exception(f"Failed to generate magic link: {str(e)}") from e

    def generate_recovery_link(self, email: str) -> str:
        """Build a password reset link for Resend templates (does not email via Supabase)."""
        try:
            response = self.__service_client.auth.admin.generate_link(
                {
                    "type": "recovery",
                    "email": email,
                    "options": {
                        "redirect_to": f"https://{self._frontend_url}/reset-password",
                    },
                }
            )
            return response
        except Exception as e:
            raise Exception(f"{str(e)}") from e

    def create_user(self, email: str, password: str) -> User:
        """Creates a new user in the authentication system using the Supabase client."""
        response = None
        try:
            response = self._client.auth.sign_up({"email": email, "password": password})
            return response.user
        except Exception as e:
            if response and hasattr(response, "id"):
                # delete the user if it was created but an error occurred later
                self.delete_user(response.id)
            raise Exception(f" {str(e)}")

    def delete_user(self, user_id: str) -> None:
        """Deletes a user from the authentication system using the Supabase client."""
        try:
            self.__service_client.auth.admin.delete_user(user_id)
        except Exception as e:
            raise Exception(f"Failed to delete auth user: {str(e)}")

    def login_user(self, email: str, password: str) -> User:
        """Logs in a user using the Supabase client and returns the user object."""
        try:
            response = self._client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            return response
        except Exception as e:
            raise Exception(f"Failed to login user: {str(e)}")

    def refresh_token(self, refresh_token: str) -> User:
        """Refreshes the user's authentication token using the Supabase client."""
        try:
            if not refresh_token:
                raise Exception("Refresh token is required")
            response = self._client.auth.refresh_session(refresh_token)
            return response
        except Exception as e:
            raise Exception(f"Failed to refresh token: {str(e)}")

    def logout_user(self) -> None:
        """Logs out the current user using the Supabase client."""
        try:
            self._client.auth.sign_out()
        except Exception as e:
            raise Exception(f"Failed to logout user: {str(e)}")

    def email_verification(self, email: str) -> None:
        """Sends an email verification email to the user using the Supabase client."""
        try:
            self._client.auth.resend({"type": "signup", "email": email})
        except Exception as e:
            raise Exception(f"Failed to send email verification: {str(e)}")

    def confirm_email_verification(self, token: str, email: str) -> None:
        """Confirms the email verification using the provided token and email."""
        try:
            self._client.auth.verify_otp(
                {
                    "email": email,
                    "token": token,
                    "type": "email",
                }
            )
        except Exception as e:
            raise Exception(f"Failed to confirm email verification: {str(e)}")

    def reset_password(self, email: str) -> None:
        """Sends a password reset email to the user using the Supabase client."""
        try:
            self._client.auth.reset_password_for_email(
                email,
                options={"redirectTo": f"https://{self._frontend_url}/reset-password"},
            )
        except Exception as e:
            raise Exception(f"Failed to send password reset email: {str(e)}")

    def confirm_password_reset(self, session_id: dict, new_password: str) -> None:
        """Confirms the password reset using refresh token (works if access token expired on the form)."""
        try:
            refresh_token = session_id.get("refresh_token")
            access_token = session_id.get("token")
            if not refresh_token:
                raise Exception("Refresh token is required")

            # Access tokens can expire while the user types; refresh first.
            try:
                self._client.auth.refresh_session(refresh_token)
            except Exception:
                if access_token:
                    self._client.auth.set_session(
                        access_token=access_token,
                        refresh_token=refresh_token,
                    )
                else:
                    raise

            self._client.auth.update_user({"password": new_password})
            self._client.auth.sign_out()

        except Exception as e:
            raise Exception(f"Failed to confirm password reset: {str(e)}") from e

    def passwordless_login(self, email: str) -> None:
        """Sends a passwordless login email to the user using the Supabase client."""
        try:
            print(f"Attempting passwordless login for email: {email}")
            response = self._client.auth.sign_in_with_otp(
                {
                    "email": email,
                    "options": {
                        # set this to false if you do not want the user to be automatically signed up
                        "should_create_user": False,
                        "email_redirect_to": f"https://{self._frontend_url}/login",
                    },
                }
            )
            return response

        except Exception as e:
            raise Exception(f"Failed to send passwordless login email: {str(e)}")
