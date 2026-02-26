
from fastapi import FastAPI
from . import routers
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

app = FastAPI()

origins = ["*"] 

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

@app.get("/")
def root():
    return RedirectResponse(url="/redoc")

app.include_router(routers.post_router)
app.include_router(routers.user_router)
app.include_router(routers.auth_router)
app.include_router(routers.vote_router)

