"""
Database configuration and session management.
This module establishes the connection to the PostgreSQL database using SQLModel 
(which wraps SQLAlchemy) and provides a dependency for managing database sessions.
"""
from sqlmodel import SQLModel, create_engine, Session
from .config import settings

# Construct the exact URL required by SQLAlchemy to connect to PostgreSQL.
# We securely build this using the validated environment variables from config.py.
DATABASE_URL = (
    f"postgresql://{settings.database_username}:{settings.database_password}@"
    f"{settings.database_hostname}:{settings.database_port}/{settings.database_name}"
)

# The 'engine' is the core interface to the database. It manages the connection pool.
# By default, create_engine does not actually connect to the DB until the first query is run.
engine = create_engine(DATABASE_URL)

def get_session():
    """
    FastAPI Dependency: Generates a new database session for each request.
    
    Why use 'yield'?: Using 'yield' instead of 'return' turns this into a generator. 
    It allows FastAPI to inject the session into the router, let the router do its work, 
    and then automatically close the session when the request finishes—even if an error occurs!
    This prevents database memory leaks and connection pool exhaustion.
    """
    with Session(engine) as session:
        yield session