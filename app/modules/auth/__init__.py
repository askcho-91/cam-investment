from supabase import create_client, Client
from gotrue.types import User
from os import getenv


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

    def _absolute_redirect(self, path: str) -> str:
        explicit_login = getenv("LOGIN_URL", "").strip()
        explicit_reset = getenv("RESET_PASSWORD_URL", "").strip()
        if path in ("/login", "login") and explicit_login:
            return explicit_login
        if path in ("/reset-password", "reset-password") and explicit_reset:
            return explicit_reset

        normalized = path if path.startswith("/") else f"/{path}"
        if self._frontend_url.startswith("http"):
            base = self._frontend_url.rstrip("/")
        else:
            base = f"https://{self._frontend_url.lstrip('/')}"
        return f"{base}{normalized}"

    def _extract_action_link(self, response) -> str:
        properties = getattr(response, "properties", None)
        if properties is not None:
            link = getattr(properties, "action_link", None)
            if link:
                return link
        if isinstance(response, dict):
            props = response.get("properties") or {}
            link = props.get("action_link")
            if link:
                return link
        raise Exception("Supabase generate_link did not return action_link")

    def _extract_user_id(self, response) -> str:
        user = getattr(response, "user", None)
        if user is not None:
            uid = getattr(user, "id", None)
            if uid:
                return str(uid)
        if isinstance(response, dict):
            user_data = response.get("user") or {}
            uid = user_data.get("id")
            if uid:
                return str(uid)
        raise Exception("Supabase generate_link did not return user id")

    def generate_magic_link_with_user(self, email: str) -> tuple[str, str]:
        """Build a magic link and return (action_link, supabase_user_id)."""
        try:
            response = self.__service_client.auth.admin.generate_link(
                {
                    "type": "magiclink",
                    "email": email,
                    "options": {"redirect_to": self._absolute_redirect("/login")},
                }
            )
            return self._extract_action_link(response), self._extract_user_id(response)
        except Exception as e:
            raise Exception(f"Failed to generate magic link: {str(e)}") from e

    def generate_magic_link(self, email: str) -> str:
        """Build a one-click sign-in link for Resend templates (does not email via Supabase)."""
        link, _ = self.generate_magic_link_with_user(email)
        return link

    def generate_recovery_link(self, email: str) -> str:
        """Build a password reset link for Resend templates (does not email via Supabase)."""
        try:
            response = self.__service_client.auth.admin.generate_link(
                {
                    "type": "recovery",
                    "email": email,
                    "options": {
                        "redirect_to": self._absolute_redirect("/reset-password"),
                    },
                }
            )
            return self._extract_action_link(response)
        except Exception as e:
            raise Exception(f"Failed to generate recovery link: {str(e)}") from e

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
            raise Exception(f"Failed to create auth user: {str(e)}")

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
