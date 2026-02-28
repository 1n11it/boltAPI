"""
Test module for Voting functionality.
This file contains tests to ensure users can vote on posts, cannot vote twice on the same post,
and can successfully remove their vote.
"""
import pytest
from fastapi.testclient import TestClient
from fastapi import status
from app.main import app

@pytest.fixture
def client():
    """
    Pytest fixture to create a fresh TestClient for each test.
    This allows us to make mock HTTP requests to our FastAPI app without running the actual server.
    """
    yield TestClient(app)

def test_vote_on_post(client):
    """
    Tests the complete lifecycle of a vote on a post:
    1. Authenticate user.
    2. Create a fresh target post.
    3. Add a new vote (Success).
    4. Attempt to vote again on the same post (Conflict).
    5. Remove the vote (Success).
    """
    # --- STEP 1: Authenticate the User ---
    # We need a valid JWT token because the voting endpoint requires a logged-in user.
    login_res = client.post(
        "/login", 
        data={"username": "hello@gmail.com", "password": "password123"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # --- STEP 2: Create a Target Post ---
    # To test voting, we must have a post that actually exists in the database.
    # Creating a fresh post here ensures our test is isolated and doesn't rely on existing DB data.
    post_res = client.post(
        "/post/", 
        json={"title": "Test Post", "content": "Voting test content"}, 
        headers=headers
    )
    post_data = post_res.json()
    
    # Validate the response structure before proceeding to avoid unexpected KeyErrors later.
    assert "Post" in post_data
    post_id = post_data["Post"]["id"]

    # --- STEP 3: Test Adding a Vote (dir = 1) ---
    # The 'dir' (direction) value of 1 means the user is liking the post.
    vote_res = client.post(
        "/vote/", 
        json={"post_id": post_id, "dir": 1}, 
        headers=headers
    )
    assert vote_res.status_code == status.HTTP_201_CREATED
    assert vote_res.json()["message"] == "Successfully added vote"

    # --- STEP 4: Test Duplicate Vote Conflict (dir = 1 again) ---
    # A user should not be able to like the same post multiple times.
    # The system should catch this and return a 409 Conflict.
    repeat_vote = client.post(
        "/vote/", 
        json={"post_id": post_id, "dir": 1}, 
        headers=headers
    )
    assert repeat_vote.status_code == status.HTTP_409_CONFLICT

    # --- STEP 5: Test Removing a Vote (dir = 0) ---
    # The 'dir' value of 0 means the user is un-liking or removing their vote.
    delete_vote = client.post(
        "/vote/", 
        json={"post_id": post_id, "dir": 0}, 
        headers=headers
    )
    assert delete_vote.status_code == status.HTTP_201_CREATED
    assert delete_vote.json()["message"] == "Successfully deleted vote"