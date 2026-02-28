"""
Database Models (ORM / Table Definitions).
This module defines the actual PostgreSQL database schema using SQLModel 
(which acts as a bridge combining Pydantic's syntax with SQLAlchemy's power).

Whenever you see `table=True`, it means this class directly translates into 
a physical table in your database.
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import text

# ==========================================
# POST TABLE
# ==========================================

class Post(SQLModel, table=True):
    """
    Represents the 'posts' table in the database.
    Contains the core content created by users.
    """
    # Overriding the default class name to ensure the table is plural lowercase.
    __tablename__ = "posts"
    
    # Why Optional?: In Python, before we commit this object to the DB, it doesn't 
    # have an ID yet. SQLAlchemy assigns it automatically upon insert.
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # --- REFERENTIAL INTEGRITY ---
    # foreign_key: Enforces that a post must belong to a valid user.
    # ondelete="CASCADE": Crucial for database cleanup! If a User is deleted, 
    # PostgreSQL will automatically delete all of their posts to prevent "orphaned" data.
    owner_id: int = Field(foreign_key="users.id", ondelete="CASCADE", nullable=False)
    
    title: str = Field(nullable=False)
    content: str = Field(nullable=False)
    
    # --- DEFAULT VALUES ---
    # default=True: Handles the default value in Python before reaching the database.
    # server_default: Tells PostgreSQL to use "true" if raw SQL inserts data without this column.
    published: bool = Field(default=True, sa_column_kwargs={"server_default": text("true")})
    
    # default_factory: Ensures a fresh UTC timestamp is generated exactly when the Python object is made.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        sa_column_kwargs={"server_default": text("now()")}
    )
    
    # --- ORM RELATIONSHIPS (Not actual columns!) ---
    # This tells SQLAlchemy to automatically fetch the related User object when we query a Post.
    # 'back_populates' ensures a two-way sync: Post knows its owner, User knows their posts.
    owner: "User" = Relationship(back_populates="posts")

# ==========================================
# USER TABLE
# ==========================================

class User(SQLModel, table=True):
    """
    Represents the 'users' table in the database.
    Handles authentication details and acts as the parent for Posts and Votes.
    """
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # --- DATABASE CONSTRAINTS & PERFORMANCE ---
    # unique=True: The database fundamentally blocks duplicate emails. 
    # index=True: We query by email every time someone logs in. Indexing this column 
    # makes that search lighting-fast (O(log n) instead of O(n) table scan).
    email: str = Field(nullable=False, unique=True, index=True)
    
    password: str = Field(nullable=False)
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), 
        sa_column_kwargs={"server_default": text("now()")}
    )
    
    # Link back to the Post model. A single user can have multiple posts (List).
    posts: list["Post"] = Relationship(back_populates="owner")

# ==========================================
# VOTE (LIKES) TABLE
# ==========================================

class Vote(SQLModel, table=True):
    """
    Represents the 'votes' junction table.
    This manages the Many-to-Many relationship between Users and Posts.
    """
    __tablename__ = "votes"
    
    # --- COMPOSITE PRIMARY KEY (The "One Vote" Logic) ---
    # By setting primary_key=True on BOTH user_id and post_id, we create a Composite Primary Key.
    # This acts as an iron-clad database constraint. 
    # It mathematically guarantees that a specific user can only have ONE row for a specific post.
    # If they try to vote twice, PostgreSQL will instantly throw an IntegrityError.
    
    user_id: int = Field(foreign_key="users.id", primary_key=True, ondelete="CASCADE")
    post_id: int = Field(foreign_key="posts.id", primary_key=True, ondelete="CASCADE")