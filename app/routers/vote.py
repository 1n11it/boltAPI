
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from ..database import  get_session
from ..models import Post, User, Vote
from ..schemas import VoteCreate
from .. import oauth2

router = APIRouter(prefix="/vote", tags=["Vote"])

@router.post("/", status_code=status.HTTP_201_CREATED)
def vote(vote: VoteCreate, session: Session = Depends(get_session),current_user: User = Depends(oauth2.get_current_user)):
    post = session.get(Post, vote.post_id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post with id {vote.post_id} does not exist")
    vote_query = select(Vote).where(Vote.post_id == vote.post_id, Vote.user_id == current_user.id)
    found_vote = session.exec(vote_query).first()
    if vote.dir == 1:
        if found_vote:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"You already have a vote on post {vote.post_id}")
        new_vote = Vote(post_id=vote.post_id, user_id=current_user.id)
        session.add(new_vote)
        session.commit()
        return {"message": "Successfully added vote"}
    else:
        if not found_vote:
            raise HTTPException(status_code=404, detail="Vote does not exist")
        session.delete(found_vote)
        session.commit()
        return {"message": "Successfully deleted vote"}