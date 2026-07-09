from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from sqlalchemy.orm import Session as ses
from datetime import datetime, timedelta

from src.database import get_db
from src.models import NewsLetter, ContactMessage, Comments
from config import get_user_agent, create_token, logger, decode_token
from src.schemas import CreateComment


user_bp = APIRouter(prefix="/user")

@user_bp.post("/create")
async def create_user(request:Request, response:Response, user:dict, db:ses=Depends(get_db)):
    try:
        ip_address = request.client.host
        user_agent_str = request.headers.get("user-agent")
        ua = get_user_agent(user_agent_str)
        email = user.get("email")
        logdata = {"role":"user", "email":"", "id":None}
        
        existing_user = db.query(NewsLetter).filter(NewsLetter.email == email).first()
        
        if existing_user:
            logdata['email'] = existing_user.email,
            logdata['id'] = existing_user.id
            
            access_token = create_token(user_data=logdata, exps=60*60*24*365)
        
            response.set_cookie(
                key="access_token",
                value=access_token,
                samesite='none',
                secure=True,
                httponly=True,
                max_age=60*60*24*365 )
            
            logger.info(f"user {existing_user.email} loged in")
            return {"detail":"Thanks for reaching out again"}
        
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
        
        logdata["email"] = new_user.email
        logdata["id"] = new_user.id
        access_token = create_token( user_data=logdata, exps=60*60*24*365)
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            samesite='none',
            secure=True,
            httponly=True,
            max_age=60*60*24*365
        )
        
        logger.info(f"New user {new_user.email} Register")
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
        
        if newsletter:
            if existing_newsletter_user:
                existing_newsletter_user.name = user.get("name")
            elif not existing_newsletter_user:
                new_newsletter_user = user
                new_newsletter_user['status'] = 'subscribed'
                new_newsletter_user = NewsLetter(**new_newsletter_user)
                db.add(new_newsletter_user)
        
        db.commit()
        return {"detail":"I'd reveice your message and we will reach out to you soon"}
    
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
@user_bp.post("/comment")
async def added_comment(request:Request, commentObj:CreateComment, db:ses=Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        payload = {}
        if token:
            payload = decode_token(token)
        
        new_comment = commentObj.dict()
        user_email = payload.get("email") if payload else None
        new_comment.update({"user_email":user_email})
        
        db_comment = Comments(
            **new_comment
        )
        db.add(db_comment)
        db.commit()
        db.flush(db_comment)
        
        logger.info("New Comment added")
        msg = """
        Your comment was receive.
        If you will like a response send use message via the contact page or sign up for newsletter.
        """
        return {"detail":msg}
    except HTTPException:
        db.rollback()
        logger.exception("db error")
        raise
    
    except Exception as e:
        logger.exception("an error occur")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )