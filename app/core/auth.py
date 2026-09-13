
from firebase_admin import auth as firebase_auth, credentials
import firebase_admin
from pathlib import Path
import json
import firebase_admin
from firebase_admin import credentials
import os

cred_json = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"])
cred = credentials.Certificate(cred_json)
firebase_admin.initialize_app(cred)


def verify_firebase_jwt(token: str) -> dict:
    decoded = firebase_auth.verify_id_token(token)
    if not decoded.get("email_verified"):
        raise ValueError("Email not verified")
    return {
        "provider": "firebase",
        "provider_id": decoded["uid"],
        "email": decoded["email"],
    }