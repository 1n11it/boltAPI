
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, col
from sqlalchemy import func
from typing import List, Optional
from ..database import  get_session
from ..models import Post, User, Vote
from ..schemas import PostCreate, PostOut
from .. import oauth2

router = APIRouter(prefix="/post", tags=["Post"])

@router.get("/", response_model=List[PostOut])
def get_posts(session: Session = Depends(get_session),current_user: User = Depends(oauth2.get_current_user), limit: int = 10, skip: int=0, 
    search: Optional[str] = ""):
    statement = (
        select(Post, func.count(Vote.post_id).label("votes"))
        .join(Vote, Post.id == Vote.post_id , isouter=True)
        .group_by(Post.id)
        .where(col(Post.title).contains(search))
        .limit(limit).offset(skip)
    )
    posts = session.exec(statement).all()
    return posts

@router.get("/{id}", response_model=PostOut)
def get_post(id: int, session:Session = Depends(get_session),current_user: User = Depends(oauth2.get_current_user)):
    statement = (
        select(Post, func.count(Vote.post_id).label("votes"))
        .join(Vote, Post.id == Vote.post_id , isouter=True)
        .group_by(Post.id)
        .where(Post.id == id)
    )
    post = session.exec(statement).first()
    if not post:
        raise HTTPException(status_code=404, detail=f"Post with id {id} does not exist")
    return post

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=PostOut)
def create_post(post: PostCreate, session: Session = Depends(get_session),current_user: User = Depends(oauth2.get_current_user)):
    new_post = Post(**post.model_dump(),owner_id=current_user.id)
    session.add(new_post)
    session.commit()
    session.refresh(new_post)
    return {"Post": new_post, "votes": 0}

@router.put("/{id}", response_model=PostOut)
def update_post(id: int,post: PostCreate, session: Session = Depends(get_session),current_user: User = Depends(oauth2.get_current_user)):
    db_post = session.get(Post, id)
    if not db_post:
        raise HTTPException(status_code=404, detail=f"Post with id {id} does not exist")
    if db_post.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform requested action")
    post_data = post.model_dump(exclude_unset=True)
    db_post.sqlmodel_update(post_data)
    session.add(db_post)
    session.commit()
    session.refresh(db_post)
    vote_count_query = select(func.count(Vote.post_id)).where(Vote.post_id == id)
    vote = session.exec(vote_count_query).one()
    return {"Post": db_post, "votes": vote}

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(id: int, session: Session = Depends(get_session),current_user: User = Depends(oauth2.get_current_user)):
    post = session.get(Post, id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post with id {id} does not exist")
    if post.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform requested action")
    session.delete(post)
    session.commit()
    return None