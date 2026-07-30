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
        comments = db.query(Comments).order_by(Comments.created_at.desc()).limit(7)
        visitors = db.query(SiteVisit).order_by(SiteVisit.created_at.desc()).limit(7)
        settings = db.query(Setting).all()
        
        
        
        info = {
            "contacts": [contact.to_dict() for contact in contacts],
            "newsletter": [newsletter.to_dict() for newsletter in newsletter],
            "tags": [tag.to_dict() for tag in tags],
            "posts": [post.to_dict() for post in posts],
            "settings": [setting.to_dict() for setting in settings],
            "comments": [comment.to_dict() for comment in comments],
            "visitors": [visitor.to_dict() for visitor in visitors],
            
            "posts_count": posts.count(),
            "comments_count": comments.count(),
            "tags_count": tags.count() | 0,
            "contacts_count": contacts.count(),
            "newsletters_count": newsletter.count(),
            "views": sum([post.views for post in posts ]),
            "visitor_count":visitors.count()
        }
        logger.info("get analytics request succeded.")
        return info
    except Exception as e:
        logger.exception(f"An error occur at {get_analytics.__name__}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )

from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

@admin_bp.get("/vendors/analytic")
async def get_vendors_analytic(request: Request, db: Session = Depends(get_db)):
    try:
        # 1. Authorization & Token Verification
        token = request.cookies.get("access_token")
        if not token:
            logger.warning(f"Unauthorized Access Attempt | IP: {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to access this resource."
            )

        payload = decode_token(token)
        if not payload or payload.get("role") != "admin":
            logger.warning(f"Forbidden Admin Access Attempt | IP: {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required."
            )

        # 2. Database Aggregations & Summary Counts
        total_sales = db.query(func.coalesce(func.sum(Orders.money), 0.0)).scalar()
        active_products_count = db.query(Products).count()
        registered_vendors_count = db.query(Vendor).count()
        pending_reviews_count = db.query(Products).count()
        

        # 3. Data Slices for Admin Dashboard Tabs
        recent_products = (
            db.query(Products)
            .order_by(Products.created_at.desc())
            .limit(20)
            .all()
        )

        recent_vendors = (
            db.query(Vendor)
            # .filter(Vendor.role == "vendor")
            .order_by(Vendor.created_at.desc())
            .limit(20)
            .all()
        )

        recent_orders = (
            db.query(Orders)
            .order_by(Orders.created_at.desc())
            .limit(10)
            .all()
        )
        # 4. Construct Response Data for Admin UI
        response_data = {
            "metrics": {
                "total_sales": f"${total_sales:,.2f}",
                "active_products": active_products_count,
                "registered_vendors": registered_vendors_count,
                "pending_reviews": pending_reviews_count,
            },
            "products": [
                product.to_dict()
                for product in recent_products
            ],
            "vendors": [
                {
                    **vendor.to_dict(),
                    # "status": getattr(vendor, 'status', 'Approved'),
                    "productsCount": db.query(Products).filter(Products.vendor_id == vendor.id).count(),
                }
                for vendor in recent_vendors
            ],
            "recent_orders": [order.to_dict() for order in recent_orders]
        }

        logger.info("Admin analytics request succeeded.")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"An error occurred at")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve analytics data."
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
@admin_bp.delete("/delete/product")
async def delete_product(product_id:int, request:Request, db:ses=Depends(get_db)):
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
        
        product = db.query(Products).filter(Products.id == product_id).first()
        if not product:
            logger.warning(product)
            raise HTTPException(
                status_code=404,
                detail="user not found"
            )
        
        db.delete(product)
        db.commit()

        logger.warning(f"admin {payload.get("email")} deleted {product.product_name}")
        return {"detail":"Contact deleted"}
    except HTTPException:
        db.rollback()
        logger.exception("Error occur")
        raise HTTPException(
            status_code=400,
            detail="Sorry somethong went wrong"
        )

@admin_bp.patch("/publish_post")
async def pulish_post(post_id:int, request:Request, db:ses=Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        if not token:
            logger.warning("not token found")
            raise HTTPException(status_code=401)
        
        payload = decode_token(token)
        if not payload or payload.get("role") != "admin":
            logger.warning("unauthorized attempt")
            raise HTTPException(status_code=401, detail="user not allow")
        
        post = db.query(Posts).filter(Posts.id==int(post_id)).first()
        if not post:
            logger.warning("post not found to published")
            raise HTTPException(status_code=404, detail="Post ot found to published")
        
        if post.status == 'true':
            post.status = False
        else:
            post.status = True
        
        db.commit()
        
    except HTTPException:
        db.rollback()   
        logger.exception("error occur")
        raise
    except Exception as e:
        logger.exception("bad error occur")
        raise HTTPException(status_code=400, detail=str(e))
