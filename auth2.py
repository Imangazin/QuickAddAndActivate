import os
import time
import uuid

import jwt
import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
KID = os.getenv("KID")
SCOPES = os.getenv("SCOPES")
TOKEN_URL = os.getenv(
    "BRIGHTSPACE_TOKEN_URL",
    "https://auth.brightspace.com/core/connect/token",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRIVATE_KEY_FILE = os.getenv(
    "PRIVATE_KEY_FILE",
    os.path.join(BASE_DIR, "keys", "private.key"),
)


def _private_key_pem() -> str:
    with open(PRIVATE_KEY_FILE, "r", encoding="utf-8") as key_file:
        return key_file.read()


def build_client_assertion() -> str:
    now = int(time.time())
    payload = {
        "iss": CLIENT_ID,
        "sub": CLIENT_ID,
        "aud": TOKEN_URL,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + 300,
    }
    headers = {
        "kid": KID,
        "typ": "JWT",
        "alg": "RS256",
    }
    return jwt.encode(
        payload,
        _private_key_pem(),
        algorithm="RS256",
        headers=headers,
    )


def get_access_token() -> dict:
    if not CLIENT_ID:
        raise ValueError("CLIENT_ID is not configured.")
    if not KID:
        raise ValueError("KID is not configured.")
    if not SCOPES:
        raise ValueError("SCOPES is not configured.")

    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "scope": SCOPES,
            "client_assertion_type": (
                "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
            ),
            "client_assertion": build_client_assertion(),
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        timeout=30,
        allow_redirects=False,
    )
    response.raise_for_status()
    return response.json()
