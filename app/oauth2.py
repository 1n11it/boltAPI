"""
OAuth2 Authentication and JWT (JSON Web Token) Management.
This module handles the generation, verification, and extraction of JWTs 
to secure our API endpoints and identify the currently logged-in user.
"""
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from .database import get_session
from .models import User
from .schemas import TokenData
from .config import settings

# Pulling security configurations from our strictly validated Pydantic settings.
SECRET_KEY = settings.secret_key
AlGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# This defines the security scheme for FastAPI.
# The 'tokenUrl' tells the Swagger UI (/docs) where it should send the username 
# and password to receive a token. It also automatically extracts the token 
# from the 'Authorization: Bearer <token>' header in incoming HTTP requests.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

def create_access_token(data: dict) -> str:
    """
    Generates a new securely signed JWT access token.
    
    Why add an 'exp' (expiration) claim?: Tokens should never live forever. 
    If a user's token is intercepted by a malicious actor, the expiration time 
    limits the window of opportunity for the attacker to misuse it.
    
    Args:
        data (dict): The payload to encode inside the token (usually just the user_id).
        
    Returns:
        str: The encoded JWT string containing the header, payload, and cryptographic signature.
    """
    to_encode = data.copy()
    
    # Define when the token will expire. We explicitly use UTC time to avoid 
    # nasty bugs when servers are deployed in different time zones.
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Update the payload with the standard 'exp' claim.
    to_encode.update({"exp": expire})
    
    # Sign the token using our SECRET_KEY. If anyone alters the payload (e.g., trying 
    # to change their user_id to an admin's id), the signature will break, 
    # and our server will reject it.
    encode_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=AlGORITHM)
    return encode_jwt

def verify_access_token(token: str, credentials_exception):
    """
    Decodes the JWT and validates its contents.
    
    This function checks:
    1. Is the signature valid? (Has it been tampered with?)
    2. Has the token expired? (Handled automatically by the jose library)
    3. Does it contain the expected 'user_id' payload?
    """
    try:
        # Attempt to decode the token. This throws a JWTError if the token 
        # is expired, improperly formatted, or signed with the wrong/fake key.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[AlGORITHM])
        
        # Extract the user ID. We cast it to str because JWT payloads are standard JSON.
        user_id: str = payload.get("user_id")
        
        if user_id is None:
            raise credentials_exception
            
        # Validate the extracted data against our Pydantic schema to ensure data integrity.
        token_data = TokenData(id=user_id)
        
    except JWTError:
        # Catch-all for any token validation failure (expired, tampered, invalid format).
        raise credentials_exception
        
    return token_data

def get_current_user(
    token: str = Depends(oauth2_scheme), 
    session: Session = Depends(get_session)
):
    """
    FastAPI Dependency to protect routes and fetch the active user.
    
    How it works: When you add `current_user: User = Depends(get_current_user)` to a route, 
    FastAPI automatically acts as a bouncer. It extracts the token, verifies it, fetches 
    the user from the database, and injects that User object into your router function.
    
    If any step fails, it halts the request immediately and returns a 401 Unauthorized error.
    """
    # Define the exact exception to throw if anything goes wrong.
    # Adding the 'WWW-Authenticate' header is a strict HTTP standard requirement for 401 errors.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="Could not validate credentials", 
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    # Step 1: Verify the token cryptographically and extract the user ID
    token_data = verify_access_token(token, credentials_exception)
    
    # Step 2: Ensure the user actually still exists in the database.
    # Why?: A token might still be mathematically valid for 45 minutes, 
    # but if the user deleted their account 5 minutes ago, they shouldn't get access!
    user = session.get(User, token_data.id)
    
    if not user:
        raise credentials_exception
        
    return user