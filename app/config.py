"""
Global Configuration Management.
This module leverages Pydantic to strictly validate and cast environment 
variables loaded from the .env file (or system environment).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    The main settings schema for the application.
    
    Why Pydantic?: If a developer sets ACCESS_TOKEN_EXPIRE_MINUTES="45" in the .env file, 
    it is technically a string. Pydantic reads these type hints and automatically 
    casts "45" into an integer. 
    
    Furthermore, if ANY of these fields are missing from the environment, 
    FastAPI will refuse to start, preventing hidden runtime crashes.
    """
    # Database Connection Settings
    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str

    # Security and JWT Settings
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    # Tell Pydantic exactly where to look for these variables.
    # It will automatically parse the .env file in the root directory.
    model_config = SettingsConfigDict(env_file=".env")

# Instantiate the settings object exactly once.
# By importing `settings` from this file, the rest of the application 
# (like database.py and oauth2.py) can safely access strongly-typed config values.
settings = Settings()