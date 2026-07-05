from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from src.database import Base, engine
from sqlalchemy.orm import Session as session
from dotenv import load_dotenv
from datetime import datetime

from src.models import Posts
from src.database import get_db
from src.routers import all_blue_prints


load_dotenv()
origin = [
    "easitechlr.com",
    "https://www.easitechlr.com",
    "http://localhost:5173"
    ]

app = FastAPI(title="Easi Tech Lr. Blog")
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins = origin,
    allow_methods = ['*'],
    allow_headers = ['*'],
    allow_credentials = True
)

@app.get("/")
async def root():
    return {
        "status": "online",
        "app": "Easi Tech Lr API",
        "version": "1.0"
    }

@app.get("/home")
async def home(db:session=Depends(get_db), cursor:int=Query(None), limit:int=Query(ge=20, le=20, limit=100)):
    posts = db.query(Posts).order_by(Posts.id.desc()).filter(Posts.published_at<=datetime.now())
    try:
        if cursor:
            posts = posts.filter(Posts.id < cursor)
            
        posts = posts.limit(limit).all()
        posts = [s.to_dict() for s in posts]
        return {
            "posts": posts,
            "last_id": posts[-1].get("id") if posts else None,
            "has_more": len(posts) == limit
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
for bp in all_blue_prints:
    app.include_router(bp)