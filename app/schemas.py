"""
Pydantic Schemas for Data Validation and Serialization.
Unlike 'models.py' which defines actual database tables, these schemas strictly define 
the shape of incoming JSON requests (Input) and outgoing JSON responses (Output).
This acts as an automated firewall—rejecting bad data before it hits our business logic.
"""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, Annotated

# ==========================================
# AUTHENTICATION SCHEMAS
# ==========================================

class Token(BaseModel):
    """Schema for the standard OAuth2 token response."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Schema for the data embedded inside our JWT token payload."""
    id: Optional[int] = None

# ==========================================
# USER SCHEMAS
# ==========================================

class UserCreate(BaseModel):
    """
    Schema for incoming user registration requests.
    Using 'EmailStr' forces Pydantic to validate that the string actually 
    looks like an email (e.g., has an '@' and a domain) before creating the user.
    """
    email: EmailStr 
    password: str

class UserOut(BaseModel):
    """
    Schema for outgoing user data.
    Notice that 'password' is intentionally missing. By using this as a response_model, 
    FastAPI will automatically strip out the hashed password before sending it to the client.
    """
    id: int
    email: EmailStr
    created_at: datetime

class UserShort(BaseModel):
    """
    A truncated user schema used for nesting inside other responses (like Posts).
    We don't need to send the exact creation date of the user every time we fetch a post.
    """
    id: int
    email: EmailStr

# ==========================================
# POST SCHEMAS
# ==========================================

class PostCreate(BaseModel):
    """Schema for incoming requests to create or update a post."""
    title: str
    content: str
    published: bool = True

class Post(BaseModel):
    """
    Standard schema for a Post. 
    It includes a nested 'owner' field which utilizes the 'UserShort' schema.
    FastAPI will automatically resolve the SQLAlchemy relationship and nest the JSON!
    """
    id: int
    owner_id: int
    title: str
    content: str
    published: bool
    created_at: datetime
    owner: UserShort

class PostOut(BaseModel):
    """
    Schema for posts retrieved with a JOIN operation on the votes table.
    It expects a nested dictionary structure: {"Post": {post_data}, "votes": 5}
    """
    Post: Post
    votes: int

# ==========================================
# VOTE SCHEMAS
# ==========================================

class VoteCreate(BaseModel):
    """
    Schema for incoming vote requests.
    
    Why Annotated?: The 'dir' (direction) field represents liking (1) or removing a like (0).
    Using Annotated with Field(ge=0, le=1) strictly enforces that the API will 
    throw a 422 Unprocessable Entity error if a user tries to send dir=2 or dir=-1.
    """
    post_id: int
    dir: Annotated[int, Field(ge=0, le=1)]
