"""
Voting and Engagement Router.
This module handles the logic for users liking (voting for) or unliking posts.
It acts as the controller for the Many-to-Many relationship between Users and Posts,
ensuring strict data integrity and preventing duplicate votes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from ..database import  get_session
from ..models import Post, User, Vote
from ..schemas import VoteCreate
from .. import oauth2

# Grouping these endpoints under "Vote" in the Swagger UI.
router = APIRouter(prefix="/vote", tags=["Vote"])

@router.post("/", status_code=status.HTTP_201_CREATED)
def vote(
    vote: VoteCreate, 
    session: Session = Depends(get_session),
    
    # --- ROUTE PROTECTION ---
    # Enforces that anonymous users cannot vote. The JWT token is verified, 
    # and the authenticated User object is injected directly into this function.
    current_user: User = Depends(oauth2.get_current_user)
):
    """
    Casts or removes a vote on a specific post.
    
    The payload expects a 'post_id' and a 'dir' (direction).
    - dir = 1: The user wants to add a vote/like.
    - dir = 0: The user wants to remove their existing vote/like.
    """

    # Step 1: Referential Integrity Check
    # Before we do anything, we must ensure the post actually exists.
    # If a user tries to vote on a post that was just deleted by its owner,
    # the database would throw a Foreign Key constraint error. We catch it gracefully here.
    post = session.get(Post, vote.post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Post with id {vote.post_id} does not exist"
        )
        
    # Step 2: Query for an Existing Vote
    # We check the junction table to see if a row already exists matching 
    # BOTH the targeted post AND the current authenticated user.
    vote_query = select(Vote).where(
        Vote.post_id == vote.post_id, 
        Vote.user_id == current_user.id
    )
    found_vote = session.exec(vote_query).first()
    
    # Step 3: Branching Logic based on the 'dir' (Direction) parameter
    if vote.dir == 1:
        # --- ADDING A VOTE ---
        
        # Conflict Prevention: If the vote already exists, they can't like it again.
        # We return a 409 Conflict because the request is trying to create a duplicate 
        # state that violates our business logic.
        if found_vote:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"You already have a vote on post {vote.post_id}"
            )
            
        # Create the new vote record in the junction table.
        new_vote = Vote(post_id=vote.post_id, user_id=current_user.id)
        session.add(new_vote)
        session.commit()
        return {"message": "Successfully added vote"}
        
    else:
        # --- REMOVING A VOTE (dir == 0) ---
        
        # Logical Check: You cannot unlike something you haven't liked yet.
        if not found_vote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Vote does not exist"
            )
            
        # Hard delete the vote record from the junction table.
        session.delete(found_vote)
        session.commit()
        return {"message": "Successfully deleted vote"}