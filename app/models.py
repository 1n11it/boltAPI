
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import text

class Post(SQLModel, table=True):
    __tablename__ = "posts"
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id", ondelete="CASCADE", nullable=False)
    title: str = Field(nullable=False)
    content: str = Field(nullable=False)
    published: bool = Field(default=True, sa_column_kwargs={"server_default": text("true")})
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column_kwargs={"server_default": text("now()")})
    owner: "User" = Relationship(back_populates="posts")

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(nullable=False, unique=True, index=True)
    password: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), sa_column_kwargs={"server_default": text("now()")})
    posts: list["Post"] = Relationship(back_populates="owner")

class Vote(SQLModel, table=True):
    __tablename__ = "votes"
    user_id: int = Field(foreign_key="users.id" , primary_key=True, ondelete="CASCADE")
    post_id: int = Field(foreign_key="posts.id" , primary_key=True, ondelete="CASCADE")


