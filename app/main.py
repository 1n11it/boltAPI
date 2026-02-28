"""
Main Application Entry Point.
This file initializes the FastAPI application, configures global middleware 
(like CORS for frontend communication), and wires together all the modular 
routers (Users, Posts, Auth, Votes) into a single cohesive API.

HOW TO RUN LOCALLY:
uvicorn app.main:app --reload
"""
from fastapi import FastAPI
from . import routers
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

# Initialize the core FastAPI application instance.
# This 'app' object is what ASGI servers like Uvicorn or Gunicorn look for to run the server.
app = FastAPI()

# ==========================================
# CORS (Cross-Origin Resource Sharing) SETUP
# ==========================================

# Origins define which external domains are allowed to talk to this API.
# Using ["*"] means this is a PUBLIC API that accepts requests from any website.
# PRO TIP: In a strict production environment where only YOUR frontend should 
# access the API, you would change this to something like: ["https://myfrontend.com"]
origins = ["*"] 

# Middleware acts like a global filter that processes every single request 
# before it reaches our routers, and every response before it leaves.
app.add_middleware(
    CORSMiddleware,
    # Allow the domains listed in the 'origins' list above
    allow_origins=origins,
    # Allow cookies and authentication headers to be sent cross-origin
    allow_credentials=True,
    # Allow all HTTP methods (GET, POST, PUT, DELETE, OPTIONS, etc.)
    allow_methods=["*"], 
    # Allow all headers (like Authorization, Content-Type, etc.)
    allow_headers=["*"], 
)

# ==========================================
# GLOBAL ROUTES
# ==========================================

@app.get("/", tags=["Root"])
def root():
    """
    Root Endpoint.
    """
    return RedirectResponse(url="/redoc")

# ==========================================
# ROUTER INTEGRATION
# ==========================================
# Here we plug in all of our modular routing files. 
# This prevents our main.py from becoming a 5,000-line monster file!
# Every endpoint defined in these routers will now be served by the application.

app.include_router(routers.post_router)
app.include_router(routers.user_router)
app.include_router(routers.auth_router)
app.include_router(routers.vote_router)

