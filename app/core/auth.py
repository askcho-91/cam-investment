import jwt
from jwt import PyJWKClient, PyJWTError
from os import getenv
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = getenv("SUPABASE_URL")
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"

jwks_client = PyJWKClient(JWKS_URL)

def verify_auth_jwt(token: str) -> dict:
    try:
       
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            key=signing_key.key,
            algorithms=["ES256"],
            audience="authenticated"
        )
        return payload
    except PyJWTError as e:
        raise Exception(f"JWT verification failed: {str(e)}")