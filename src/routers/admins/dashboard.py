from fastapi import APIRouter, Request, Response, HTTPException, status, Depends, Query
from config import decode_token, logger
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
            "newsletters_count": newsletter.count(),
            "views": sum([post.views for post in posts ])
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

@admin_bp.delete("/unsubscribe")
async def unsubscribe(subscriber_id:int, request:Request, db:ses=Depends(get_db)):
    # user_agent_str =
    try:
        token = request.cookies.get("access_token")
        if not token:
            logger.warning("unauthorized attempt")
            raise HTTPException(
                status_code=401,
                detail="unauthorized attempt"
            )

        payload = decode_token(token)
        if not payload or payload.get("role") != "admin":
            logger.warning("user not authorized")
            raise HTTPException(status_code=401)
        
        unsubscriber = db.query(NewsLetter).filter(NewsLetter.id == subscriber_id).first()
        if not unsubscriber:
            logger.warning(unsubscriber)
            raise HTTPException(
                status_code=404,
                detail="user not found"
            )
        
        unsubscriber.status = "unsubscribed"
        logger.warning(f"admin {payload.get("email")} deleted {unsubscriber.email}")
        db.commit()
        resp = """"Unsubscribed, If you would like to received email on our products and service\nclick https//www.easitechlr.com/contact"""
        return {"detail":resp}
    except HTTPException:
        logger.exception("Error occur")
        raise HTTPException(
            status_code=400,
            detail="Sorry somethong went wrong"
        )
        
@admin_bp.delete("/contact")
async def delete_contact(contact_id:int, request:Request, db:ses=Depends(get_db)):
    # user_agent_str =
    try:
        token = request.cookies.get("access_token")
        if not token:
            logger.warning("unauthorized attempt")
            raise HTTPException(
                status_code=401,
                detail="unauthorized attempt"
            )

        payload = decode_token(token)
        if not payload or payload.get("role") != "admin":
            logger.warning("user not authorized")
            raise HTTPException(status_code=401)
        
        contact_user = db.query(ContactMessage).filter(ContactMessage.id == contact_id).first()
        if not contact_user:
            logger.warning(contact_user)
            raise HTTPException(
                status_code=404,
                detail="user not found"
            )
        
        db.delete(contact_user)
        db.commit()

        logger.warning(f"admin {payload.get("email")} deleted {contact_user.email}")
        return {"detail":"Contact deleted"}
    except HTTPException:
        logger.exception("Error occur")
        raise HTTPException(
            status_code=400,
            detail="Sorry somethong went wrong"
        )