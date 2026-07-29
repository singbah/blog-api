from fastapi import APIRouter, Request, Response, HTTPException, status, Depends, Query
from sqlalchemy.orm import Session as ses
from datetime import datetime, timedelta, timezone

from src.database import get_db
from src.models import NewsLetter, ContactMessage, Comments, Vendor, Products, Orders
from config import get_user_agent, create_token, logger, decode_token,  MAX_ATTEMPT, ACCOUNT_LOCK_DELAY
from src.schemas import CreateComment

user_bp = APIRouter(prefix="/user")

@user_bp.post("/create")
async def create_user(request:Request, response:Response, user:dict, db:ses=Depends(get_db)):
    try:
        ip_address =  request.client.host if request.client else "No IP"
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
        db.refresh(new_user)
        
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
        ip_address = request.client.host if request.client else "NO IP"
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
        db.refresh(db_comment)
        
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

@user_bp.get("/me")
async def get_user(request:Request, db:ses=Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        payload = None
        if token:
            payload = decode_token(token)
            
        if not token or not payload:
            logger.warning("Token not found")
            raise HTTPException(status_code=401, detail="Auths require")
            
        user = db.query(Vendor).where(Vendor.id == payload.get("id")).first()
        if not user or user.is_block:
            raise HTTPException(status_code=401, detail="User Unavaliable")
        
        return user.to_dict(['hash_password'])
            
    except Exception as e:
        logger.exception("error occur")
        raise HTTPException(status_code=500, detail=str(e))

@user_bp.get("/complete_transaction")
async def complete_transaction(order_id:str, resquest:Request, db:ses=Depends(get_db)):
    try:
        if not order_id:
            logger.warning("You didn't send order id")
            print("You didn't send order id")
            raise HTTPException(status_code=404, detail="order unavaliable")
        
        order = db.query(Orders).filter(Orders.order_id==order_id).first()
        if not order:
            logger.warning("order not avaliable in db")
            print("order not avaliable in db")
            raise HTTPException(status_code=404, detail="Order is unavaliable")
        
        order.status = 'paid'
        order.updated_at = datetime.now(timezone.utc)
        db.commit()
        return {"detail":"Order's checked"}
    except Exception as e:
        db.rollback()
        logger.exception("error occur")
        raise HTTPException(status_code=500, detail=str(e))
        

@user_bp.get("/vendor_analytic")
async def vendor_analytic(
    request:Request, 
    cursor:int=Query(default=0), 
    limit:int=Query(le=20, limit=100), 
    db:ses=Depends(get_db)):
    try:
        now = datetime.now(timezone.utc)
        week_day = now + timedelta(days=9)
        
        token = request.cookies.get("access_token")
        payload = decode_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="You need token to access this info")
        
        user = db.query(Vendor).filter(Vendor.id == payload.get("id")).first()
        if user and user.is_deleted or user.is_block:
            logger.warning(f"deleted account attempt to get info")
            raise HTTPException(status_code=423, detail="Unavaliable")
        
        products = db.query(Products).filter(Products.vendor_id==payload.get("id")).where(Products.id > cursor).order_by(Products.created_at.desc()).limit(limit).all()
        
        orders = db.query(Orders).where(Orders.vendor_id==payload.get("id")).order_by(Orders.created_at.desc()).limit(10).all()
        
        my_orders = db.query(Orders).where(Orders.user_phone==user.phone).order_by(Orders.created_at.desc()).limit(10).all()
        
        total_sales = sum([float(order.money) for order in orders if order.status == 'paid' ])
        expenditure = sum([float(order.money) for order in my_orders if order.status == 'paid' ])
        total_product_customers_order=sum([product.quantity for product in orders])
        total_products_order=sum([product.quantity for product in my_orders])
        profit_margin = float(total_sales-expenditure)
        pending_customers_orders = len([order for order in orders if order.status == 'pending'])
        pending_orders = len([order for order in my_orders if order.status == 'pending'])
        
        sales_record = {"total_sales":total_sales, 
                        "expenditure":expenditure, 
                        "profit_margin":profit_margin,
                        'total_product_customers_order':total_product_customers_order,
                        'total_products_order':total_products_order,
                        'pending_orders':pending_orders,
                        'pending_customers_orders':pending_customers_orders
                        }
        
        print(sales_record)
        
        return{'product':[p.to_dict() for p in products], 
               "customers_orders":[order.to_dict() for order in orders],
               "customer_orders_count":len(orders),
               "user_orders":[m_order.to_dict() for m_order in my_orders],
               "user_orders_count":len(my_orders),
               "product_count":len(products),
               "cursor":products[-1].id if products else 0,
               "sales_record":sales_record
               }
    
    except Exception as e:
        db.rollback()
        logger.exception("error occur")
        raise HTTPException(status_code=500, detail=str(e))
