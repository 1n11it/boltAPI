# =====================================================================
# BOLT API - DOCKER CONFIGURATION
# =====================================================================
# This Dockerfile defines the environment and step-by-step instructions 
# to build the container image for our FastAPI application.
# =====================================================================

# Step 1: Base Image Selection
# We use a specific, official Python image (trixie) to ensure consistency.
# Pinning the exact version (3.14.3) prevents unexpected breaking changes 
# if a newer, incompatible version of Python is released in the future.
FROM python:3.14.3-trixie

# Step 2: Set Working Directory
# All subsequent commands (COPY, RUN, CMD) will be executed inside this 
# specific directory within the isolated container environment.
WORKDIR /app

# Step 3: Copy Dependencies First (Optimization Step)
# PRO TIP: We copy ONLY the requirements.txt file first, rather than all code.
# This leverages Docker's layer caching mechanism. If we only change our Python code 
# but don't add new packages, Docker will use the cached layer for the 'pip install' 
# step, drastically speeding up subsequent build times!
COPY requirements.txt .

# Step 4: Install Dependencies
# The '--no-cache-dir' flag tells pip not to save the downloaded installation 
# archives locally. This is crucial for keeping our final Docker image size 
# as small and lightweight as possible.
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy Application Source Code
# Now that dependencies are installed and cached, we copy the rest of our 
# application code into the container's working directory.
# IMPORTANT: Ensure you have a `.dockerignore` file in your root folder 
# to prevent copying local `venv/`, `.env`, and `__pycache__/` files into the image.
COPY . .

# Step 6: Expose Port
# This acts as developer documentation indicating that the application inside 
# the container will listen on port 8000. 
# Note: This does NOT automatically publish the port to the host machine.
EXPOSE 8000

# Step 7: Define the Startup Command
# This command runs the Uvicorn ASGI server to start our FastAPI application.
# Binding the host to "0.0.0.0" is mandatory in Docker; otherwise, the app 
# will only be accessible from inside the container itself (localhost loopback).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]