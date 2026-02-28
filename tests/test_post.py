"""
Test module for Post (Social Media Content) functionality.
This file contains integration tests for all CRUD (Create, Read, Update, Delete) 
operations related to posts, as well as strict authorization checks to ensure 
users can only modify their own data.
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

# --- HELPER FUNCTION ---
def get_token(client, email="hello@gmail.com", password="password123"):
    """
    Helper function to authenticate a user and retrieve a JWT access token.
    
    Why this exists: Applying the DRY (Don't Repeat Yourself) principle. 
    Almost every post-related test requires an authenticated user, so extracting 
    the login process here keeps our test cases clean and focused.
    """
    res = client.post("/login", data={"username": email, "password": password})
    return res.json()["access_token"]

# ==========================================
# TEST CASES
# ==========================================

def test_get_all_posts_unauthorized(client):
    """
    Security Test: Ensure unauthenticated users cannot access the posts feed.
    The system should block the request at the dependency level before hitting the router logic.
    """
    res = client.get("/post/")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

def test_create_post(client):
    """
    Tests the creation of a new post and validates the nested response structure.
    
    Why nested validation?: Our API returns a joined schema `{"Post": {...}, "votes": 0}` 
    instead of a flat post object. This test ensures that the nesting logic works perfectly.
    """
    # Step 1: Get a valid JWT token
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 2: Send POST request to create a resource
    res = client.post(
        "/post/", 
        json={"title": "New Post", "content": "Nice content"}, 
        headers=headers
    )
    assert res.status_code == status.HTTP_201_CREATED
    
    # Step 3: Validate the nested Pydantic response (PostOut schema)
    data = res.json()
    assert "Post" in data
    assert data["Post"]["title"] == "New Post"
    assert data["votes"] == 0  # A brand new post must inherently have 0 votes

def test_get_one_post(client):
    """
    Tests fetching a specific post by its ID.
    We create a fresh post first to ensure the ID we are querying actually exists.
    """
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 1: Seed the database with a test post
    post_res = client.post("/post/", json={"title": "Get One", "content": "Content"}, headers=headers)
    post_id = post_res.json()["Post"]["id"]

    # Step 2: Fetch the newly created post and verify the ID matches
    res = client.get(f"/post/{post_id}", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["Post"]["id"] == post_id

def test_update_post(client):
    """
    Tests the PUT operation to modify an existing post's details.
    """
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 1: Create a baseline post
    post_res = client.post("/post/", json={"title": "Old Title", "content": "Content"}, headers=headers)
    post_id = post_res.json()["Post"]["id"]

    # Step 2: Send PUT request with updated fields
    update_res = client.put(
        f"/post/{post_id}", 
        json={"title": "New Title", "content": "Content"}, 
        headers=headers
    )
    
    # Step 3: Verify the title was successfully modified in the database response
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.json()["Post"]["title"] == "New Title"

def test_delete_post(client):
    """
    Tests the DELETE operation and verifies actual database removal.
    It's not enough to just check for a 204 status; we must aggressively query 
    the deleted resource to ensure it returns a 404.
    """
    token = get_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 1: Create a post meant to be deleted
    post_res = client.post("/post/", json={"title": "Delete Me", "content": "Content"}, headers=headers)
    post_id = post_res.json()["Post"]["id"]

    # Step 2: Issue the delete command (Expect 204 No Content)
    del_res = client.delete(f"/post/{post_id}", headers=headers)
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    # Step 3: Double-check! Try to fetch it again to confirm physical/logical deletion
    get_res = client.get(f"/post/{post_id}", headers=headers)
    assert get_res.status_code == status.HTTP_404_NOT_FOUND

def test_delete_other_user_post(client):
    """
    CRITICAL SECURITY CHECK: Cross-User Authorization.
    Verifies that User A cannot delete User B's post. The API must enforce 
    ownership validation (post.owner_id == current_user.id).
    """
    # Step 1: User 1 (hello@gmail.com) authenticates and creates a post
    token1 = get_token(client, "hello@gmail.com", "password123")
    headers1 = {"Authorization": f"Bearer {token1}"}
    post_res = client.post("/post/", json={"title": "User 1 Post", "content": "Content"}, headers=headers1)
    post_id = post_res.json()["Post"]["id"]

    # Step 2: User 2 (duplicate@gmail.com) authenticates
    # (Assuming duplicate@gmail.com already exists in the test DB environment)
    token2 = get_token(client, "duplicate@gmail.com", "password123")
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Step 3: User 2 attempts a malicious delete operation on User 1's post
    del_res = client.delete(f"/post/{post_id}", headers=headers2)
    
    # Step 4: Validate that the router intercepts this and throws a 403 Forbidden
    assert del_res.status_code == status.HTTP_403_FORBIDDEN