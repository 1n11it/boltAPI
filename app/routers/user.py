
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from ..database import  get_session
from ..models import User
from ..schemas import UserCreate, UserOut
from .. import utils

router = APIRouter(prefix="/user", tags=["User"])

@router.get("/{id}", response_model=UserOut)
def get_user(id: int, session:Session = Depends(get_session)):
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id {id} does not exist")
    return user

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    hashed_password = utils.hash_password(user.password)
    user.password = hashed_password
    db_user = User.model_validate(user)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

