from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from sqlalchemy.orm import Session as ses
from datetime import datetime, timedelta

from src.database import get_db
from src.models import NewsLetter, ContactMessage
from config import get_user_agent


user_bp = APIRouter(prefix="/user")

@user_bp.post("/create")
async def create_user(request:Request, user:dict, db:ses=Depends(get_db)):
    try:
        ip_address = request.client.host
        user_agent_str = request.headers.get("user-agent")
        ua = get_user_agent(user_agent_str)
        
        email = user.get("email")
        
        existing_user = db.query(NewsLetter).filter(NewsLetter.email == email).first()
        
        if existing_user:
            print(existing_user.to_dict())
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exist in database"
            )
        
    
        if not user.get("name").strip() or user.get("name") == "":
            user['name'] = 'user'
        
        now = datetime.now()
        
        user['ip_address'] = ip_address
        user['user_agent'] = str(ua)
        user['status'] = 'subscribed'
        # user['last_open'] = now
        
        new_user = NewsLetter(**user)
        db.add(new_user)
        db.commit()
        db.flush(new_user)
        
        print(new_user.to_dict())
        return{"detail":"Thanks for reaching out i will reply you soon.."}
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@user_bp.post("/contact")
async def create_contact(request:Request, user:dict, db:ses=Depends(get_db)):
    try:
        new_contact = {}
        ua = get_user_agent(request.headers.get("user-agent"))
        ip_address = request.client.host
        newsletter = user.get("newsletter")
        email = user.get("email")
        
        existing_newsletter_user = db.query(NewsLetter).filter(NewsLetter.email==email).first()
        
        user['status'] = 'New'
        user['ip_address'] = ip_address  
        user['user_agent'] = ua      
        print('user:', user)
        
        if existing_newsletter_user:
            existing_newsletter_user.name = user.get("name")
            
        new_newsletter_user = user
        new_newsletter_user['status'] = 'subscribed'
        print('newsletter user:', new_newsletter_user)
        
        
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )