from fastapi import APIRouter, Request, Response, HTTPException, status, Depends, Query
from config import decode_token, send_email, logger
from src.database import get_db
from src.models import *
from sqlalchemy.orm import Session as ses


admin_bp = APIRouter(prefix="/admin")

@admin_bp.get("/settings")
async def get_settings(request:Request, db:ses=Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource"
            )
        
        payload = decode_token(token)
        if not payload or payload.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource"
            )
        
        settings = db.query(Setting).all()
        return [s.to_dict() for s in settings]
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )


@admin_bp.get("/analytics")
async def get_analytics(request:Request, db:ses=Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        if not token:
            # logger.log(f"unanthorized attempt on route {get_analytics.__name__}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource"
            )
        
        payload = decode_token(token)
        if not payload or payload.get("role") != "admin":
            # logger.log(f"unanthorized attempt get_analytics route")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource"
            )
        
        contacts = db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).limit(7)
        newsletter = db.query(NewsLetter).order_by(NewsLetter.created_at.desc()).limit(7)
        tags = db.query(Tags).order_by(Tags.created_at.desc()).limit(7)
        posts = db.query(Posts).order_by(Posts.created_at.desc()).limit(7)
        settings = db.query(Setting).all()
        
        info = {
            "contacts": [contact.to_dict() for contact in contacts],
            "newsletter": [newsletter.to_dict() for newsletter in newsletter],
            "tags": [tag.to_dict() for tag in tags],
            "posts": [post.to_dict() for post in posts],
            "settings": [setting.to_dict() for setting in settings],
            
            "posts_count": posts.count(),
            "tags_count": tags.count() | 0,
            "contacts_count": contacts.count(),
            "newsletters_count": newsletter.count()
        }
        return info
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )

# GET ALL CONTACTS
@admin_bp.get("/all-contacts")
async def get_all_contacts(request:Request, cursor:int=Query(None), limit:int=Query(limit=100), db:ses=Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        if not token:
            logger.info("unauthorization attempt on get all contacts route")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource"
            )
        
        payload = decode_token(token)
        if not payload or payload.get("role") != "admin":
            logger.error("unauthorization attempt on get all contacts route")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource"
            )
        
        query = db.query(ContactMessage).order_by(ContactMessage.created_at.desc())
        
        if cursor:
            query = query.filter(ContactMessage.id < cursor)
        
        contacts = query.limit(limit).all()
        
        return {
            "contacts": [contact.to_dict() for contact in contacts],
            "last_id": contacts[-1].to_dict().get("id"),
            "has_more": len(contacts) == limit
        }
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )

# GET ALL NEWSLETTER
@admin_bp.get("/all-newsletters")
async def get_all_newsletters(request:Request, cursor:int=Query(None), limit:int=Query(ge=20, le=10, limit=100), db:ses=Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        if not token:
            logger.error(f"Unauthorized attempt on route: get all newsletters")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource"
            )
        
        payload = decode_token(token)
        if not payload or payload.get("role") != "admin":
            logger.error(f"Unauthorized attempt on route: get all newsletters")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource"
            )

        query = db.query(NewsLetter).order_by(NewsLetter.created_at.desc())
        
        if cursor:
            query = query.filter(NewsLetter.id < cursor)
        
        newsletters = query.limit(limit).all()
        
      
        return {
            "newsletters": [newsletter.to_dict() for newsletter in newsletters],
            "cursor": newsletters[-1].get("id") if newsletters else None,
            "has_more": len(newsletters) == limit
        }
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )

# SEND NEWSLETTER EMAIL
@admin_bp.post("/send_newsletter")
async def send_newsletter_email(user:dict, request:Request, db:ses=Depends(get_db)):
    try:
        token = request.headers.get("access_token")
        ip_address = request.client.host
        
        if not token:
            error_message = f"IP ADDRESS {ip_address} attempted {send_newsletter_email.__name__}"
            logger.error(error_message)
            raise HTTPException(
                status_code=401,
                detail="You are not authorized to access this source"
            )
        payload = decode_token(token)
        if not payload or payload.get("role") != 'admin':
            error_message = f"IP ADDRESS {ip_address} attempted {send_newsletter_email.__name__}"
            logger.error(error_message)
            raise HTTPException(
                status_code=401,
                detail="You are not authorized to access this source")
            
        await send_email(
            recipients=[user.get("email")],
            subject=user.get("subject"),
            template_name="newsletter.html",
            context={
                "name":user.get("name"),
                "website":"http://127.0.0.1:8000/",
                "body":user.get("message")
            }
        )
        
        logger.info(f"email sent to subscriber - ${user.name}")
        return {"detail":"Email Send"}
     
    except Exception as e:
        logger.info(f"Email not sent, error occur: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )