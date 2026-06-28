from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from src.database import Base, engine
from sqlalchemy.orm import Session as session
from dotenv import load_dotenv
import os

from src.models import Posts
from src.database import get_db
from src.routers import all_blue_prints


load_dotenv()
origin = os.getenv('ORIGINS')

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
async def root(db:session=Depends(get_db)):
    settings = db.query(Posts).order_by(Posts.created_at.desc()).all()
    try:
        settings = [s.to_dict(['']) for s in settings]
        return settings
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
for bp in all_blue_prints:
    app.include_router(bp)