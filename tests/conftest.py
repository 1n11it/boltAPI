"""
Pytest Configuration and Global Fixtures.
This file acts as the 'Control Center' for all tests.
KEY COMPONENTS:
- Database Session: Handles per-test isolation and data cleanup.
- Engine: Core SQLAlchemy interface for the test database.
- Client Factory: Provides both standard and Pre-Authorized (JWT) TestClients.
- Authentication: Manages automatic user creation and token generation.
"""
import pytest
from sqlmodel import Session, delete, create_engine
from app.main import app
from app.database import get_session, engine
from app.config import settings
from app.models import User, Post, Vote
from fastapi.testclient import TestClient

# Pointing specifically to  test database
DATABASE_URL = (
    f"postgresql://{settings.database_username}:{settings.database_password}@"
    f"{settings.database_hostname}:{settings.database_port}/boltapi_test"
)

engine = create_engine(DATABASE_URL)

@pytest.fixture(name="session")
def session_fixture():
    """
    Provides a clean database session for each test.
    
    HOW IT WORKS:
    1. It opens a transaction with the database.
    2. It yields the session to the test function.
    3. AFTER the test finishes, it runs the DELETE commands to wipe the tables.
    
    Why use delete() instead of drop_all()?: Manual deletion is significantly faster
    for local development and Docker environments while maintaining Foreign Key safety.
    """
    with Session(engine) as session:
        # --- TEARDOWN / CLEANUP ---
        # We delete data in reverse order of relationships to avoid IntegrityErrors.
        # Votes depend on Posts/Users, so they go first.
        session.exec(delete(Vote))
        session.exec(delete(Post))
        session.exec(delete(User))
        session.commit()
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