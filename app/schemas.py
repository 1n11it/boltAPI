
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, Annotated

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[int] = None

class UserCreate(BaseModel):
    email: EmailStr 
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

class UserShort(BaseModel):
    id: int
    email: EmailStr

class PostCreate(BaseModel):
    title: str
    content: str
    published: bool = True

class Post(BaseModel):
    id: int
    owner_id: int
    title: str
    content: str
    published: bool
    created_at: datetime
    owner: UserShort

class PostOut(BaseModel):
    Post: Post
    votes: int

class VoteCreate(BaseModel):
    post_id: int
    dir: Annotated[int, Field(ge=0, le=1)]
