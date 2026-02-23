
from sqlmodel import SQLModel, create_engine, Session
from .config import settings

DATABASE_URL = (
    f"postgresql://{settings.database_username}:{settings.database_password}@"
    f"{settings.database_hostname}:{settings.database_port}/{settings.database_name}"
)

engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session
