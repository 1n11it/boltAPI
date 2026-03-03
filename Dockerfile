# =====================================================================
# BOLT API - DOCKER CONFIGURATION
# =====================================================================
# This Dockerfile defines the environment and step-by-step instructions 
# to build the container image for our FastAPI application.
# =====================================================================

# Step 1: Base Image Selection
# We use a specific, official Python image (slim) to ensure consistency.
# Pinning the exact version (3.14.3) prevents unexpected breaking changes 
# while keeping the image size drastically smaller for efficient deployment.
FROM python:3.14.3-slim

# Step 2: Install System Utilities
# PRO TIP: 'netcat-traditional' allows our entrypoint script to check if 
# the database port is open before running migrations. This prevents 
# 'Connection Refused' crashes during cold starts.
RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

# Step 3: Set Working Directory
# All subsequent commands (COPY, RUN, CMD) will be executed inside this 
# specific directory within the isolated container environment.
WORKDIR /app

# Step 4: Copy Dependencies First (Optimization Step)
# PRO TIP: We copy ONLY the requirements.txt file first, rather than all code.
# This leverages Docker's layer caching mechanism. If we only change our Python code 
# but don't add new packages, Docker will use the cached layer for the 'pip install' 
# step, drastically speeding up subsequent build times!
COPY requirements.txt .

# Step 5: Install Dependencies
# The '--no-cache-dir' flag tells pip not to save the downloaded installation 
# archives locally. This is crucial for keeping our final Docker image size 
# as small and lightweight as possible.
RUN pip install --no-cache-dir -r requirements.txt

# Step 6: Copy Application Source Code
# Now that dependencies are installed and cached, we copy the rest of our 
# application code into the container's working directory.
# IMPORTANT: Ensure you have a `.dockerignore` file in your root folder 
# to prevent copying local `venv/`, `.env`, and `__pycache__/` files into the image.
COPY . .

# Step 7: Final Permissions & Formatting
# IMPORTANT: This ensures the entrypoint script is executable within the 
# Linux environment, regardless of the host OS (Windows/Mac) it was built on.
RUN chmod +x /app/entrypoint.sh

# Step 8: Expose Port
# This acts as developer documentation indicating that the application inside 
# the container will listen on port 8000. 
# Note: This does NOT automatically publish the port to the host machine.
EXPOSE 8000

# Step 9: Define the Startup Orchestration
# We use ENTRYPOINT to run our 'gatekeeper' script (entrypoint.sh) 
# and CMD to run the Uvicorn ASGI server to start our FastAPI application.
# This ensures that even if we override the command to run tests or a 
# shell, the database readiness and migrations logic will ALWAYS execute first.
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]