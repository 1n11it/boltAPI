"""
User Management Router.
This module handles the creation (registration) of new users and retrieving
user profiles. It heavily utilizes Pydantic response models to ensure 
sensitive data (like passwords) never leaks to the client.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from ..database import  get_session
from ..models import User
from ..schemas import UserCreate, UserOut
from .. import utils
from .. import oauth2

# Setting a prefix means we don't have to type "/user" in every route below.
# The tags argument groups these endpoints neatly in the Swagger UI.
router = APIRouter(prefix="/user", tags=["User"])

@router.get("/{id}", response_model=UserOut)
def get_user(
    id: int, 
    session: Session = Depends(get_session), 
    
    # --- ROUTE PROTECTION ---
    # Even though we don't strictly use the `current_user` variable in the function body,
    # declaring it as a dependency forces FastAPI to validate the user's JWT token.
    # This means anonymous (unlogged) users cannot scrape user profiles.
    current_user: User = Depends(oauth2.get_current_user)
):
    """
    Fetch a specific user's profile by their ID.
    
    This is a protected route. Only authenticated users can view profiles.
    Because `response_model=UserOut` is set, FastAPI will automatically strip out 
    the hashed password before sending the JSON back to the client.
    """
    # Fetch the user directly using their primary key.
    user = session.get(User, id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User with id {id} does not exist"
        )
        
    return user

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=UserOut)
def create_user(
    user: UserCreate, 
    session: Session = Depends(get_session)
):
    """
    Registers a new user in the system.
    
    This function performs a critical pre-check for duplicate emails and ensures 
    that the user's password is cryptographically hashed before it ever touches the database.
    """
    
    # Step 1: Pre-emptive Duplicate Check
    # We explicitly check if the email exists to return a clean 400 Bad Request error.
    # If we didn't do this, the database would throw a nasty 500 Internal Server Error 
    # when it hits the 'unique=True' constraint on the email column.
    statement = select(User).where(User.email == user.email)
    existing_user = session.exec(statement).first() 
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="User with this email already exists"
        )
        
    # Step 2: Security - Hash the password
    # NEVER store plain-text passwords. We overwrite the Pydantic model's 
    # plain password with the newly generated bcrypt hash.
    hashed_password = utils.hash_password(user.password)
    user.password = hashed_password
    
    # Step 3: Convert Pydantic Schema -> SQLModel Database Object
    db_user = User.model_validate(user)
    
    # Step 4: Database Transaction Lifecycle
    session.add(db_user)   # Stage the data
    session.commit()       # Physically write it to the PostgreSQL database
    
    # Step 5: Refresh the object
    # Why refresh?: Before committing, `db_user` didn't have an `id` or `created_at` 
    # timestamp because the database generates those. Refreshing pulls those 
    # newly generated values back into our Python object so we can return them!
    session.refresh(db_user)
    
    return db_user

