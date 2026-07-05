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
            logger.warning(f"Fail Access {get_analytics.__name__} | IP ADDRESS {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource"
            )
        
        payload = decode_token(token)
        if not payload or payload.get("role") != "admin":
            logger.warning(f"Fail Access | IP ADDRESS {request.client.host}")
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
        logger.info("get analytics request succeded.")
        return info
    except Exception as e:
        logger.exception(f"An error occur at {get_analytics.__name__}")
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
            logger.exception(f"unanthorized attempt get_analytics route IP ADDRESS {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource"
            )
        
        payload = decode_token(token)
        if not payload or payload.get("role") != "admin":
            logger.exception(f"unanthorized attempt on {get_all_contacts.__name__} route. IP ADDRESS {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource"
            )
        
        query = db.query(ContactMessage).order_by(ContactMessage.created_at.desc())
        
        if cursor:
            query = query.filter(ContactMessage.id < cursor)
        
        contacts = query.limit(limit).all()
        logger.info("Get All contact ran successfully")
        return {
            "contacts": [contact.to_dict() for contact in contacts],
            "last_id": contacts[-1].to_dict().get("id"),
            "has_more": len(contacts) == limit
        }
        
    except Exception as e:
        logger.exception("and error occur")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )

# GET ALL NEWSLETTER
@admin_bp.get("/all-newsletters")
async def get_all_newsletters(request:Request, cursor:int=Query(None), limit:int=Query(limit=100), db:ses=Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        if not token:
            logger.exception(f"Unauthorized attempt on route: get all newsletters IP ADDRESS [{request.client.host}]")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource"
            )
        
        payload = decode_token(token)
        if not payload or payload.get("role") != "admin":
            logger.warning(f"decoding token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource"
            )

        query = db.query(NewsLetter).order_by(NewsLetter.created_at.desc())
        
        if cursor:
            query = query.filter(NewsLetter.id < cursor)
        
        newsletters = query.limit(limit).all()
        
        logger.info("news letter loaded")
        return {
            "newsletters": [newsletter.to_dict() for newsletter in newsletters],
            "cursor": newsletters[-1].to_dict().get("id") if newsletters else None,
            "has_more": len(newsletters) == limit
        }
    except Exception as e:
        logger.exception("Error occur her")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )

# SEND NEWSLETTER/CONTACT EMAIL
@admin_bp.post("/send_newsletter")
async def send_newsletter_email(user:dict, request:Request, db:ses=Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        ip_address = request.client.host
        
        if not token:
            error_message = f"IP ADDRESS {ip_address} | Token Failed {send_newsletter_email.__name__}"
            logger.warning(error_message)
            raise HTTPException(
                status_code=401,
                detail="You are not authorized to access this source"
            )
        payload = decode_token(token)
        if not payload or payload.get("role") != 'admin':
            error_message = f"IP ADDRESS {ip_address} | Payload Not Found {send_newsletter_email.__name__}"
            logger.warning(error_message)
            raise HTTPException(
                status_code=401,
                detail="You are not authorized to access this source")
            
        
        user_type = user_type = (user.get("type") or "").lower()

        if not user_type:
            logger.warning("user type error")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user type error"
            )
            
        if user_type == "newsletter":
            db_user = db.query(NewsLetter).filter(NewsLetter.email==user.get("email")).first()
            db_user.last_open = datetime.now(timezone.utc)
            await send_email(
                recipients=[user.get("email")],
                subject=user.get("subject"),
                template_name="newsletter.html",
                context={
                    "name":user.get("name"),
                    "website":"easitechlr.com/blog",
                    "body":user.get("message")
                }
            )
        else:
            db_user = db.query(ContactMessage).filter(ContactMessage.email==user.get("email")).first()
            if not db_user:
                logger.warning(f"user with email {user.get("email")} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found!!"
                )
            db_user.status = "Emailed"
            await send_email(
                recipients=[user.get("email")],
                subject=user.get("subject"),
                template_name="contact_email.html",
                context={
                    "name":user.get("name"),
                    "website":"easitechlr.com/contact",
                    "body":user.get("message")
                }
            )
            
        db.commit()
        logger.info(f"Admin {payload.get("email")} emailed {user.get("name")}")
        return {"detail":"Email Send"}
     
    except HTTPException:
        db.rollback()
        logger.warning("DB error occur")
        raise
     
    except HTTPException:
        logger.exception(f"Sending Email Failed")
        raise HTTPException(
            status_code=500
        )