"""
Test module for Post (Social Media Content) functionality.
This file contains integration tests for all CRUD (Create, Read, Update, Delete) 
operations related to posts, as well as strict authorization checks to ensure 
users can only modify their own data.
"""
import pytest
from fastapi import status
from app.schemas import PostOut
from app.models import Post
from sqlalchemy import func

# ==========================================
# READ & LISTING TEST CASES
# ==========================================

def test_get_one_post_not_found(authorized_client, session):
    """
    DYNAMIC ROBUSTNESS: Max ID + 1.
    This query finds the highest ID currently in the DB and adds 1.
    It is impossible for this ID to exist at this exact moment.
    """
    # Get the current maximum ID from the database
    max_id = session.exec(func.max(Post.id)).scalar() or 0
    non_existent_id = max_id + 1
    
    res = authorized_client.get(f"/post/{non_existent_id}")
    
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json().get("detail") == f"Post with id {non_existent_id} does not exist"

def test_get_one_post(authorized_client, setup_post):
    """
    Test fetching a specific post by its ID.
    """
    res = authorized_client.get(f"/post/{setup_post['id']}")
    
    post = PostOut(**res.json())
    assert res.status_code == status.HTTP_200_OK
    assert post.Post.id == setup_post['id']
    assert post.Post.title == setup_post['title']

def test_get_one_post_unauthorized(client, setup_post):
    """
    Ensure unauthenticated users cannot access individual post.
    """
    # Remove the 'Bearer' token provided by 'authorized_client'.
    client.headers = {}
    res = client.get(f"/post/{setup_post['id']}")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_all_posts(authorized_client):
    """
    Verification: Confirms authenticated users can retrieve the feed.
    Validates that the response list adheres to the PostOut schema structure.
    """
    # Seed data
    unique_title = "Secret Testing Post"
    authorized_client.post("/post/", json={"title": unique_title, "content": "Checking existence"})
    
    res = authorized_client.get("/post/")
    assert res.status_code == status.HTTP_200_OK
    
    # Schema validation for the entire list
    posts = [PostOut(**p) for p in res.json()]
    assert len(posts) > 0
    assert posts[0].Post.title == unique_title

def test_get_all_posts_unauthorized(client):
    """
    Security Test: Ensure unauthenticated users cannot access the posts feed.
    The system should block the request at the dependency level before hitting the router logic.
    """
    res = client.get("/post/")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

# ==========================================
# CREATE & SCHEMA VALIDATION
# ==========================================

@pytest.mark.parametrize("title, content, published", [
    ("Awesome Post", "Some content", True),
    ("Favorite Pizza", "I love pepperoni", False),
    ("Default Check", "This has no published key", None), # None means we won't send the key
])
def test_create_post(authorized_client, test_user, title, content, published):
    """
    Tests the creation of a new post and validates the nested response structure.
    
    Why nested validation?: Our API returns a joined schema `{"Post": {...}, "votes": 0}` 
    instead of a flat post object. This test ensures that the nesting logic works perfectly.
    """
# Dynamic payload creation
    payload = {"title": title, "content": content}
    if published is not None:
        payload["published"] = published
    res = authorized_client.post("/post/", json=payload)
    
    assert res.status_code == status.HTTP_201_CREATED
    
    # ---  SCHEMA VALIDATION ---
    data = PostOut(**res.json()) # Pydantic will crash if structure is wrong
    assert data.Post.title == payload["title"]
    assert data.Post.owner_id == test_user["id"]
    assert data.Post.owner.email == test_user["email"] # Verifying nested UserShort schema
    assert data.votes == 0

    # Default value check: if we didn't send 'published', it should be True by default
    expected_published = published if published is not None else True
    assert data.Post.published == expected_published

def test_create_post_unauthorized(client):
    """
    Ensures anonymous users cannot create posts.
    """
    res = client.post("/post/", json={"title": "Hack", "content": "I am not logged in"})
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

# ==========================================
# CRUD & OWNERSHIP ISOLATION
# ==========================================

def test_update_post_not_found(authorized_client, session):
    """
    Get Max ID + 1 from the DB and hit it. 
    Authenticated user should get a 404.
    """
    # Dynamic non-existent ID generation
    max_id = session.exec(func.max(Post.id)).scalar() or 0
    non_existent_id = max_id + 1
    
    update_data = {"title": "Ghost Update", "content": "Does not exist"}
    res = authorized_client.put(f"/post/{non_existent_id}", json=update_data)
    
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert res.json().get("detail") == f"Post with id {non_existent_id} does not exist"

def test_update_post_non_existent_unauthorized(client):
    """
    Without login anyone hitting any ID (even -1), 
    OAuth2 will stop them with a 401 error.
    """
    client.headers = {} # State clear
    
    # -1 is mathematically impossible for auto-incrementing DBs
    res = client.put("/post/-1", json={"title": "Hack", "content": "Hack"})
    
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    assert res.json().get("detail") == "Not authenticated"

def test_update_post(authorized_client, setup_post):
    """
    Tests the PUT operation to modify an existing post's details.
    """
    payload = {"title": "Updated Title", "content": "Updated Content"}    
    res = authorized_client.put(f"/post/{setup_post['id']}", json=payload)

    # Verify the title was successfully modified in the database response
    updated_post = PostOut(**res.json())
    assert res.status_code == status.HTTP_200_OK
    assert updated_post.Post.title == payload["title"]
    assert updated_post.Post.id == setup_post['id']

def test_update_post_unauthorized(client, setup_post):
    """
    SECURITY: Ensures anonymous users cannot modify any post.
    """
    # Remove the 'Bearer' token provided by 'authorized_client'.
    client.headers = {} 
    payload = {"title": "Hacked Title", "content": "Hacked Content"}
    res = client.put(f"/post/{setup_post['id']}", json=payload)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

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

def test_delete_post_unauthorized(client, setup_post):
    """
    SECURITY: Ensures anonymous users cannot delete any post.
    """
    # Remove the 'Bearer' token provided by 'authorized_client'.
    client.headers = {} 
    res = client.delete(f"/post/{setup_post['id']}")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

# ==========================================
# CROSS-USER AUTHORIZATION (THE "ATTACKER" TEST)
# ==========================================

def test_delete_other_user_post(authorized_client, setup_post , token2):
    """
    SCENARIO: User B (authorized_client2) tries to delete User A's post.
    Logic: Uses setup_post (owned by User A) and attempts delete with User B's token.
    """
    # 1. ATTACK: User B tries to DELETE User A's post
    headers_b = {"Authorization": f"Bearer {token2}"}
    del_res = authorized_client.delete(f"/post/{setup_post['id']}", headers=headers_b)

    # 2. VERIFY: Status must be 403 Forbidden
    assert del_res.status_code == status.HTTP_403_FORBIDDEN
    assert del_res.json().get("detail") == "Not authorized to perform requested action"

    # 3. FINAL INTEGRITY CHECK
    verify_res = authorized_client.get(f"/post/{setup_post['id']}")
    assert verify_res.status_code == status.HTTP_200_OK
    assert verify_res.json()["Post"]["title"] == setup_post["title"] 
    assert verify_res.json()["Post"]["owner_id"] == setup_post["owner_id"] # Ownership must remain intact

def test_update_other_user_post(authorized_client, setup_post, token2):
    """
    SCENARIO: User B tries to UPDATE User A's post.
    Logic: Attempts to change title/content and verifies failure.
    """
    # 1. ATTACK: User B tries to UPDATE
    headers_b = {"Authorization": f"Bearer {token2}"}
    payload = {"title": "Hacked", "content": "Modified by Attacker"}
    res = authorized_client.put(f"/post/{setup_post['id']}", json=payload, headers= headers_b)
    
    # 2. VERIFY: Status must be 403 Forbidden
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert res.json().get("detail") == "Not authorized to perform requested action"

    # 3. FINAL INTEGRITY CHECK: Verify title is UNCHANGED
    verify_res = authorized_client.get(f"/post/{setup_post['id']}")
    # Title must remain what was set in setup_post, not 'Hacked'
    assert verify_res.json()["Post"]["title"] == setup_post["title"]
    assert verify_res.json()["Post"]["owner_id"] == setup_post["owner_id"] # Ownership must remain intact