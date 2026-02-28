"""
Authentication Router.
This module handles user login and the generation of JSON Web Tokens (JWT).
It specifically implements the OAuth2 with Password (and bearer token) flow.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from ..database import  get_session
from ..models import User
from .. import utils
from .. import oauth2
from .. schemas import Token

# The tags argument groups this endpoint under "Authentication" in the Swagger UI (/docs)
router = APIRouter(tags=["Authentication"])

# NOTE: OAuth2PasswordRequestForm expects data as Form-Data, NOT a JSON body.
# It strictly requires fields named 'username' and 'password'.
@router.post('/login', response_model=Token)
def login(
    user_credentials: OAuth2PasswordRequestForm = Depends(), 
    session: Session = Depends(get_session)
):
    """
    Authenticates a user and returns a JWT Bearer token.

    This endpoint acts as the single point of entry for registered users to 
    prove their identity and gain access to protected routes.
    """
    
    # Step 1: Query the database for the user.
    # Because OAuth2 standardizes the field as 'username', we map that 
    # directly to our database's 'email' column here.
    statement = select(User).where(User.email == user_credentials.username)
    user = session.exec(statement).first()
    
    # --- SECURITY BEST PRACTICE: PREVENT ENUMERATION ATTACKS ---
    # Notice how both the "user not found" and "wrong password" checks return 
    # the EXACT same HTTP 403 error and "Invalid Credentials" detail.
    # If we returned "Email not found", a hacker could use a bot to test millions 
    # of emails just to see which ones are registered in our database. 
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Invalid Credentials"
        )
        
    # Step 2: Cryptographically verify the password against the database hash.
    if not utils.verify_password(user_credentials.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Invalid Credentials"
        )
        
    # Step 3: Credentials are valid. Generate the JWT.
    # We embed the user's primary key (id) into the token payload. 
    # This allows downstream protected routes to know EXACTLY who is making the request.
    access_token = oauth2.create_access_token(data={"user_id": user.id})
    
    # Step 4: Return the standardized OAuth2 token response.
    return {"access_token": access_token, "token_type": "bearer"}