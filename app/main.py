
from fastapi import FastAPI
from . import routers
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = ["*"] 

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

app.include_router(routers.post_router)
app.include_router(routers.user_router)
app.include_router(routers.auth_router)
app.include_router(routers.vote_router)

