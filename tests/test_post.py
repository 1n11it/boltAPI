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
from app.schemas import PostOut, PostCreate
from app.models import Post

# ==========================================
# READ & LISTING TEST CASES
# ==========================================

def test_get_all_posts_unauthorized(client):
    """
    Security Test: Ensure unauthenticated users cannot access the posts feed.
    The system should block the request at the dependency level before hitting the router logic.
    """
    res = client.get("/post/")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_all_posts_authenticated(authorized_client):
    """
    Verification: Confirms authenticated users can retrieve the feed.
    Validates that the response list adheres to the PostOut schema structure.
    """
    # Seed data
    authorized_client.post("/post/", json={"title": "Feed Post", "content": "Content"})
    
    res = authorized_client.get("/post/")
    assert res.status_code == status.HTTP_200_OK
    
    # Schema validation for the entire list
    posts = [PostOut(**p) for p in res.json()]
    assert len(posts) >= 1
    assert posts[0].Post.title == "Feed Post"

# ==========================================
# CREATE & SCHEMA VALIDATION
# ==========================================

def test_create_post(authorized_client, test_user):
    """
    Tests the creation of a new post and validates the nested response structure.
    
    Why nested validation?: Our API returns a joined schema `{"Post": {...}, "votes": 0}` 
    instead of a flat post object. This test ensures that the nesting logic works perfectly.
    """
    payload = {"title": "boltAPI Post", "content": "Testing nested schemas", "published": True}
    res = authorized_client.post("/post/", json=payload)
    
    assert res.status_code == status.HTTP_201_CREATED
    
    # ---  SCHEMA VALIDATION ---
    data = PostOut(**res.json()) # Pydantic will crash if structure is wrong
    assert data.Post.title == payload["title"]
    assert data.Post.owner_id == test_user["id"]
    assert data.Post.owner.email == test_user["email"] # Verifying nested UserShort schema
    assert data.votes == 0

# ==========================================
# CRUD & OWNERSHIP ISOLATION
# ==========================================

def test_get_one_post(authorized_client):
    """
    Test fetching a specific post by its ID.
    """
    post_res = authorized_client.post("/post/", json={"title": "Find Me", "content": "HIDEME"})
    post_id = post_res.json()["Post"]["id"]

    res = authorized_client.get(f"/post/{post_id}")
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["Post"]["id"] == post_id

def test_update_post(authorized_client):
    """
    Tests the PUT operation to modify an existing post's details.
    """
    post_res = authorized_client.post("/post/", json={"title": "Old Title", "content": "Old Content"})
    post_id = post_res.json()["Post"]["id"]
    
    update_payload = {"title": "New Title", "content": "Updated Content"}
    res = authorized_client.put(f"/post/{post_id}", json=update_payload)

    # Verify the title was successfully modified in the database response
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["Post"]["title"] == "New Title"

def test_delete_post(authorized_client):
    """
    Tests the DELETE operation and verifies actual database removal.
    It's not enough to just check for a 204 status; we must aggressively query 
    the deleted resource to ensure it returns a 404.
    """
    post_res = authorized_client.post("/post/", json={"title": "Goodbye...", "content": "Cruel World"})
    post_id = post_res.json()["Post"]["id"]

    # Delete command 
    assert authorized_client.delete(f"/post/{post_id}").status_code == status.HTTP_204_NO_CONTENT

    # Double-check! Try to fetch it again to confirm deletion
    assert authorized_client.get(f"/post/{post_id}").status_code == status.HTTP_404_NOT_FOUND

# ==========================================
# CROSS-USER AUTHORIZATION  (THE "ATTACKER" TEST)
# ==========================================

def test_delete_other_user_post(authorized_client, client, test_user):
    """
    CRITICAL SECURITY CHECK: Cross-User Authorization.
    Verifies that User B can't delete User A's post. The API must enforce 
    ownership validation (post.owner_id == current_user.id).
    """
# 1. User A (test_user) creates a post
    post_res = authorized_client.post("/post/", json={"title": "Private Post", "content": "Stay Away"})
    post_id = post_res.json()["Post"]["id"]
    token_a = authorized_client.headers.get("Authorization")

    # 2. Dynamically setup User B (The "Attacker")
    user_b = {"email": "attacker@gmail.com", "password": "password123"}
    client.post("/user/", json=user_b)
    login_res = client.post("/login", data={"username": user_b["email"], "password": user_b["password"]})
    token_b = login_res.json()["access_token"]

    # Custom headers for User B
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. ATTACK: User B tries to DELETE User A's post
    del_res = client.delete(f"/post/{post_id}", headers=headers_b)
    assert del_res.status_code == status.HTTP_403_FORBIDDEN

    # 4. ATTACK: User B tries to UPDATE User A's post
    upd_res = client.put(
        f"/post/{post_id}", 
        json={"title": "Hacked", "content": "Validating Auth, not Schema"}, 
        headers=headers_b
    )
    assert upd_res.status_code == status.HTTP_403_FORBIDDEN

    # 5. Reset Headers: We clear the base client headers just to be safe from fixture leakage
    client.headers = {}
    
    # 6. Final Integrity Check: Verify with User A that the post is still there and UNCHANGED
    authorized_client.headers = {"Authorization": token_a}
    verify_res = authorized_client.get(f"/post/{post_id}")
    assert verify_res.status_code == status.HTTP_200_OK
    assert verify_res.json()["Post"]["title"] == "Private Post" # Title must not be 'Hacked'
    assert verify_res.json()["Post"]["owner_id"] == test_user["id"] # Ownership must remain intact