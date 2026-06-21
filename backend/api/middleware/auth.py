import os
import jwt
from jwt import PyJWKClient
from fastapi import Request, HTTPException
from typing import Optional

from backend.logging_config import logger

# Global cache for JWK client
_jwk_client = None

def get_jwk_client() -> Optional[PyJWKClient]:
    """
    Loads and caches the JWK Client to retrieve signing keys from Clerk JWKS.
    """
    global _jwk_client
    if _jwk_client is not None:
        return _jwk_client
        
    jwks_url = os.getenv("CLERK_JWKS_URL")
    # If not explicitly provided, we can attempt to construct it from CLERK_PUBLISHABLE_KEY or CLERK_SECRET_KEY
    if not jwks_url:
        # For standard Clerk configurations: https://<your-clerk-frontend-api>/.well-known/jwks.json
        # The user can set CLERK_JWKS_URL in their environment variables.
        pass

    if jwks_url:
        _jwk_client = PyJWKClient(jwks_url)
    return _jwk_client

async def get_user_id(request: Request) -> Optional[str]:
    """
    Extracts and validates the Clerk JWT token from the Authorization header.
    Returns the user_id (the 'sub' claim) if valid, or None if unauthenticated.
    Supports a mock token bypass in Mock Mode or if the token starts with 'mock_'.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
        
    token = auth_header.split(" ")[1]
    if not token or token == "null" or token == "undefined":
        return None

    clerk_secret = os.getenv("CLERK_SECRET_KEY")
    
    # Check for Mock Mode or mock tokens
    if not clerk_secret or clerk_secret == "mock_key" or token.startswith("mock_"):
        if token.startswith("mock_user_"):
            return token  # Returns the custom mock user ID (e.g. mock_user_456)
        return "mock_user_123"

    try:
        jwk_client = get_jwk_client()
        if not jwk_client:
            # Fallback signature-less decoding if JWKS is not configured but a key is set
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("sub")
            
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True}
        )
        return payload.get("sub")
    except Exception as e:
        logger.warning(f"JWT Verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid authentication token: {str(e)}")

async def require_user_id(request: Request) -> str:
    """
    Dependency helper to enforce that a user is authenticated.
    """
    user_id = await get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id
