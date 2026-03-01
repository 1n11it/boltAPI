"""
Test module for Voting functionality.
This file contains tests to ensure users can vote on posts, cannot vote twice on the same post,
and can successfully remove their vote.
"""
from fastapi import status
from sqlmodel import select
from sqlalchemy import func
from app.models import Post

# ==========================================
# VOTING TEST CASES
# ==========================================

def test_vote_success(authorized_client, setup_post):
    """
    Core Logic: Ensure an authenticated user can successfully vote (dir=1).
    """
    res = authorized_client.post(
        "/vote/", 
        json={"post_id": setup_post["id"], "dir": 1}
    )
    assert res.status_code == status.HTTP_201_CREATED
    assert res.json()["message"] == "Successfully added vote"

def test_vote_twice_conflict(authorized_client, setup_post):
    """
    Constraint Check: Prevent duplicate voting.
    The system MUST return a 409 Conflict if a user tries to upvote the same post twice.
    """
    # 1st Vote (Should succeed)
    authorized_client.post("/vote/", json={"post_id": setup_post["id"], "dir": 1})
    
    # 2nd Vote (Should be blocked)
    repeat_vote = authorized_client.post("/vote/", json={"post_id": setup_post["id"], "dir": 1})
    
    assert repeat_vote.status_code == status.HTTP_409_CONFLICT

def test_delete_vote_success(authorized_client, setup_post):
    """
    Core Logic: Ensure a user can remove their existing vote (dir=0).
    """
    # 1. Add the vote first
    authorized_client.post("/vote/", json={"post_id": setup_post["id"], "dir": 1})
    
    # 2. Remove the vote
    delete_res = authorized_client.post("/vote/", json={"post_id": setup_post["id"], "dir": 0})
    
    assert delete_res.status_code == status.HTTP_201_CREATED
    assert delete_res.json()["message"] == "Successfully deleted vote"

def test_delete_non_existent_vote(authorized_client, setup_post):
    """
    Edge Case: Attempt to remove a vote that doesn't exist.
    The API should gracefully reject this rather than crashing the database.
    """
    # We send dir=0 WITHOUT ever sending dir=1 first
    res = authorized_client.post("/vote/", json={"post_id": setup_post["id"], "dir": 0})
    
    # Usually, APIs return 404 if the vote record doesn't exist to be deleted
    assert res.status_code == status.HTTP_404_NOT_FOUND

def test_vote_non_existent_post(authorized_client, session):
    """
    Security & Edge Case: Voting on a post that has been deleted or never existed.
    Uses dynamic ID discovery to guarantee a 404 Not Found response.
    """
    # Find max post ID and add 1 to guarantee it doesn't exist
    max_post_id = session.exec(select(func.max(Post.id))).one() or 0
    fake_post_id = max_post_id + 1
    
    res = authorized_client.post("/vote/", json={"post_id": fake_post_id, "dir": 1})
    assert res.status_code == status.HTTP_404_NOT_FOUND

def test_vote_unauthorized_user(client, setup_post):
    """
    Security Check: Ensure unauthenticated users cannot interact with the voting system.
    Uses the base 'client' (no token) instead of 'authorized_client'.
    """
    # Remove the 'Bearer' token provided by 'authorized_client'.
    client.headers = {}
    res = client.post("/vote/", json={"post_id": setup_post["id"], "dir": 1})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
