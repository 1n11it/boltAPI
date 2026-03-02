"""
Pytest Configuration and Global Fixtures.
This file acts as the 'Control Center' for all tests.
KEY COMPONENTS:
- DB Session Management: Implements atomic test isolation via Alembic schema resets.
- Engine Interface: Provides a dedicated SQLAlchemy connection for the test database.
- Client Factory: Generates standard and Pre-Authorized (JWT-bearing) TestClients.
- Identity Management: Automates dynamic user creation and OAuth2 token injection.
- Content Seeding: Bootstraps initial state (Posts/Votes) for complex CRUD scenarios.
"""
import pytest
from sqlmodel import Session, delete, create_engine
from app.main import app
from app.database import get_session, engine
from app.config import settings
from alembic import command
from alembic.config import Config
from app.models import User, Post, Vote
from fastapi.testclient import TestClient

# Pointing to the test database
DATABASE_URL = (
    f"postgresql://{settings.database_username}:{settings.database_password}@"
    f"{settings.database_hostname}:{settings.database_port}/{settings.database_name}"
)

engine = create_engine(DATABASE_URL)

@pytest.fixture(name="session")
def session_fixture():
    """
    Enforces a strict 'Clean Slate' policy for every test case using Alembic.
    
    Lifecycle:
    1. Setup Phase: Wipes the DB (base) and reconstructs the latest schema (head).
    2. Yield: Provides a transactional SQLModel session for the test duration.
    3. Persistence: Data is retained post-test to facilitate manual debugging.
    """
    # 1. Load Alembic config from project root
    alembic_cfg = Config("alembic.ini")
    
    # 2. Dynamic URL injection (Test DB focus)
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    
    # 3. SETUP: DB cleanup
    #  First delete everything (downgrade), then fresh tables (upgrade)
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session):
    """
    FastAPI TestClient with Dependency Overriding.
    
    This replaces the standard 'get_session' dependency in our routers with 
    the 'session' fixture above. This ensures all tests hit the clean 
    test database instead of the production one.
    """
    def get_session_override():
        return session
    
    # Inject the mock session into the FastAPI app
    app.dependency_overrides[get_session] = get_session_override
    yield TestClient(app)
    
    # Clear overrides after the test to prevent side effects in other tests
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(client):
    """
    Fixture to dynamically create a new user for any test.
    Returns a dictionary containing the user's data and their plain password.
    """
    user_data = {"email": "tester_pro@example.com", "password": "password123"}
    res = client.post("/user/", json=user_data)
    
    assert res.status_code == 201
    new_user = res.json()
    # We store the plain password because it is needed for subsequent login tests
    new_user['plain_password'] = user_data['password']
    
    return new_user

@pytest.fixture
def token(client, test_user):
    """
    Automated Login Fixture.
    Depends on 'test_user'. It logs that user in and returns a valid JWT string.
    This allows post-related tests to focus ONLY on post logic.
    """
    res = client.post("/login", data={
        "username": test_user['email'], 
        "password": test_user['plain_password']
    })
    return res.json()["access_token"]

@pytest.fixture
def authorized_client(client, token):
    """
    A pre-authenticated TestClient.
    This client already has the 'Authorization' header set, so you can 
    immediately start making requests to protected routes like /post.
    """
    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {token}"
    }
    yield client
    # Clear the headers after the test finishes so that
    # the next 'unauthorized' test gets a clean client!
    client.headers.pop("Authorization", None)

@pytest.fixture
def setup_post(authorized_client):
    """
    Setup Fixture: Creates a fresh post specifically for voting tests.
    
    Why?: By decoupling post creation from the voting tests, our tests 
    remain strictly focused on testing the 'Vote' logic, not 'Post' logic.
    """
    res = authorized_client.post(
        "/post/", 
        json={"title": "Test Post for Voting", "content": "Please vote on this"}
    )
    # Using the  router's specific nested JSON structure ("Post" key)
    return res.json()["Post"]