"""
Post (Content) Router.
This module manages the core CRUD (Create, Read, Update, Delete) operations 
for user-generated posts. It includes advanced SQL operations like Left Outer Joins 
to dynamically aggregate vote (like) counts without needing a dedicated 'likes' column.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, col
from sqlalchemy import func
from typing import List, Optional
from ..database import  get_session
from ..models import Post, User, Vote
from ..schemas import PostCreate, PostOut
from .. import oauth2

# Setting the prefix ensures all endpoints here start with /post 
router = APIRouter(prefix="/post", tags=["Post"])

@router.get("/", response_model=List[PostOut])
def get_posts(
    session: Session = Depends(get_session),
    current_user: User = Depends(oauth2.get_current_user), 
    limit: int = 10, 
    skip: int = 0, 
    search: Optional[str] = ""
):
    """
    Retrieve a paginated list of posts, including a dynamic vote count for each.
    
    Query Parameters:
    - limit: Controls pagination size (default 10).
    - skip: Controls pagination offset (default 0).
    - search: Filters posts by title matching the search string.
    """
    
    # --- ADVANCED SQL AGGREGATION ---
    # We use a LEFT OUTER JOIN (isouter=True). 
    # Why?: If we used a standard inner join, posts with 0 votes would completely 
    # disappear from the feed! The outer join ensures we get ALL posts, 
    # and func.count simply returns 0 for posts with no matching votes in the junction table.
    
    statement = (
        select(Post, func.count(Vote.post_id).label("votes"))
        .join(Vote, Post.id == Vote.post_id, isouter=True)
        .group_by(Post.id)
        .where(col(Post.title).contains(search))
        .limit(limit).offset(skip)
    )
    
    # Execute the query and fetch all matching records. 
    # FastAPI automatically structures this into the `List[PostOut]` nested schema.
    posts = session.exec(statement).all()
    return posts

@router.get("/{id}", response_model=PostOut)
def get_post(
    id: int, 
    session: Session = Depends(get_session),
    current_user: User = Depends(oauth2.get_current_user)
):
    """
    Retrieve a single specific post by its ID, along with its total vote count.
    """
    statement = (
        select(Post, func.count(Vote.post_id).label("votes"))
        .join(Vote, Post.id == Vote.post_id, isouter=True)
        .group_by(Post.id)
        .where(Post.id == id)
    )
    
    post = session.exec(statement).first()
    
    if not post:
        raise HTTPException(status_code=404, detail=f"Post with id {id} does not exist")
        
    return post

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PostOut)
def create_post(
    post: PostCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(oauth2.get_current_user)
):
    """
    Create a new post and securely associate it with the logged-in user.
    """
    # Force the 'owner_id' to be the currently authenticated user's ID.
    # This prevents malicious users from injecting a fake owner_id in the JSON body 
    # to impersonate someone else.
    new_post = Post(**post.model_dump(), owner_id=current_user.id)
    
    session.add(new_post)
    session.commit()
    session.refresh(new_post)
    
    # Return the newly created post wrapped in the expected nested dictionary format.
    # Since it was just created, we know mathematically it has 0 votes.
    return {"Post": new_post, "votes": 0}

@router.put("/{id}", response_model=PostOut)
def update_post(
    id: int,
    post: PostCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(oauth2.get_current_user)
):
    """
    Update an existing post. 
    Includes strict authorization to ensure only the creator can edit it.
    """
    # Step 1: Ensure the post exists
    db_post = session.get(Post, id)
    if not db_post:
        raise HTTPException(status_code=404, detail=f"Post with id {id} does not exist")
        
    # Step 2: STRICT AUTHORIZATION CHECK
    # This acts as a firewall. Even if a user is logged in, they cannot 
    # edit a post unless their user ID matches the post's owner ID.
    if db_post.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized to perform requested action"
        )
        
    # Step 3: Apply the updates
    post_data = post.model_dump(exclude_unset=True)
    db_post.sqlmodel_update(post_data)
    
    session.add(db_post)
    session.commit()
    session.refresh(db_post)
    
    # Step 4: Recalculate votes for the response
    # Since we are returning the PostOut schema, we need to quickly query 
    # how many votes this post has so we don't break the response contract.
    vote_count_query = select(func.count(Vote.post_id)).where(Vote.post_id == id)
    vote = session.exec(vote_count_query).one()
    
    return {"Post": db_post, "votes": vote}

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    id: int, 
    session: Session = Depends(get_session),
    current_user: User = Depends(oauth2.get_current_user)
):
    """
    Delete a specific post from the database.
    Includes strict authorization to ensure only the creator can delete it.
    """
    # Step 1: Ensure the post exists
    post = session.get(Post, id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post with id {id} does not exist")
        
    # Step 2: STRICT AUTHORIZATION CHECK
    # Prevents users from deleting other people's posts.
    if post.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized to perform requested action"
        )
        
    # Step 3: Delete the record
    # Because we set ondelete="CASCADE" in our models, PostgreSQL will automatically 
    # clean up and delete any votes associated with this post as well!
    session.delete(post)
    session.commit()
    
    # HTTP 204 No Content dictates that the response body MUST be empty.
    return None