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
        user['created_at'] = now
        user['updated_at'] = now
        user['status'] = 'subscribed'
        
        new_user = NewsLetter(**user)
        db.add(new_user)
        db.commit()
        db.flush(new_user)
        
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
        newsletter = user.get("newsletter")
        ua = get_user_agent(request.headers.get("user-agent"))
        ip_address = request.client.host
        now = datetime.now()
        email = user.get("email")
        
        existing_newsletter_user = db.query(NewsLetter).filter(NewsLetter.email==email).first()
        
        user['status'] = 'New'
        user['ip_address'] = ip_address  
        user['user_agent'] = str(ua)
        user['created_at'] = now   
        user['updated_at'] = now   
        
        new_user = ContactMessage(**user)   
        db.add(new_user)
        db.commit()
        db.flush(new_user)
        

        if newsletter:
            if existing_newsletter_user:
                existing_newsletter_user.name = user.get("name")
            elif not existing_newsletter_user:
                new_newsletter_user = user
                new_newsletter_user['status'] = 'subscribed'
                new_newsletter_user = ContactMessage(**new_newsletter_user)
                db.add(new_newsletter_user)
                db.commit()
                db.flush(new_newsletter_user)
        
        return {"detail":"I'd reveice your message and we will reach out to you soon"}
    
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )