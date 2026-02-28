"""
Test module for Root routing and Global API behavior.
This file ensures that the base URL is working correctly, redirects to the 
documentation appropriately, and handles invalid requests (wrong methods, bad paths) gracefully.
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import status
from app.main import app

@pytest.fixture
def client():
    """
    Pytest fixture to create a fresh TestClient for each test.
    """
    yield TestClient(app)

# ==========================================
# ROOT & ROUTING TEST CASES
# ==========================================

def test_root(client):
    """
    Test the main entry point (/) of the API.
    
    Why check '/redoc'?: This verifies that visiting the root URL automatically 
    redirects the user (or serves) the FastAPI ReDoc documentation page. 
    This is a great UX practice for public-facing APIs.
    """
    res = client.get("/")
    assert res.status_code == status.HTTP_200_OK
    
    # Confirm that the router correctly handled the request and landed on the documentation path
    assert res.url.path == "/redoc"

def test_root_invalid_method(client):
    """
    Security & Routing Test: Ensure the root endpoint restricts HTTP methods.
    Since the root only expects a GET request, sending a POST must be rejected.
    """
    res = client.post("/")
    # FastAPI automatically handles this and should return a 405 Method Not Allowed
    assert res.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

def test_root_with_garbage_query(client):
    """
    Robustness Test: Verify how the API handles unexpected query parameters.
    
    Why this is important: Bots and web scrapers often append random query strings 
    to URLs. The API should simply ignore them and return a 200 OK, rather than 
    crashing or throwing a 500 Internal Server Error.
    """
    # Simulating a malicious or poorly formed URL request
    res = client.get("/?nonsense=true&evil=hack")
    assert res.status_code == status.HTTP_200_OK

def test_root_invalid_path(client):
    """
    Global Error Handling Test: Ensure requests to non-existent routes are caught.
    This verifies that FastAPI's default 404 handler is functioning correctly.
    """
    res = client.get("/this/path/does/not/exist/12345")
    
    # Verify standard 404 status
    assert res.status_code == status.HTTP_404_NOT_FOUND
    # Verify the JSON detail structure matches FastAPI's default error schema
    assert res.json() == {"detail": "Not Found"}