"""
Utility functions for cryptographic operations.
This module handles sensitive data transformations, specifically focusing on 
secure password hashing and verification using the bcrypt algorithm.
"""
import bcrypt

def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using bcrypt with an automatically generated salt.
    
    Why bcrypt?: Unlike MD5 or SHA-256, bcrypt is computationally expensive. 
    This intentional slowness protects user passwords from dictionary and 
    brute-force attacks if the database is ever compromised.
    
    Args:
        password (str): The raw, plain-text password provided by the user.
        
    Returns:
        str: The fully hashed password (including the salt), safe for database storage.
    """
    # Step 1: Bcrypt requires bytes, not standard Python strings.
    pwd_bytes = password.encode('utf-8')
    
    # Step 2: Generate a random salt. A salt ensures that if two users have the 
    # same password (e.g., "password123"), their final hashes will look completely different.
    salt = bcrypt.gensalt()
    
    # Step 3: Perform the actual hashing operation.
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    
    # Step 4: Decode back to a standard string so it can be easily saved 
    # in our PostgreSQL database's VARCHAR field.
    return hashed_password.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compares a plain-text login attempt against the securely hashed password in the DB.
    
    How it works: The bcrypt algorithm is smart enough to extract the original 'salt' 
    from the `hashed_password` string. It applies that exact salt to the `plain_password` 
    and checks if the resulting hashes match.
    
    Returns:
        bool: True if passwords match, False otherwise.
    """
    # Both inputs must be encoded to bytes before comparison.
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )