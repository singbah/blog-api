from fastapi import APIRouter, Request, Response, HTTPException, status, Depends, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as session
from src.models import Products, Vendor, Orders
from src.database import get_db
from datetime import datetime, timedelta
from src.schemas import CreateOrder, CreateComment
from uuid import uuid4
import re
from config import ALLOW_EXTENSTION, MAX_ATTEMPT, MAX_LENGTH, logger, decode_token
from config.utilities import upload_to_r2

products_bp = APIRouter(prefix="/api/products", tags=["Products BluePrint"])

@products_bp.get("/listings")
async def get_listings(request:Request, cursor:int=Query(default=0), limit:int=Query(le=20, limit=100), db:session=Depends(get_db)):
    try:
        products = db.query(Products).where(Products.id > cursor).order_by(Products.updated_at.desc()).limit(limit)
        
        
        response = {"listings":[product.to_dict() for product in products], "cursor":0, "limit":20}
        return response
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@products_bp.get("/product/{productSlug}")
async def get_product(request:Request, productSlug:str, db:session=Depends(get_db)):
    try:
        product = db.query(Products).where(Products.slug == productSlug).first()
        if not product:
            raise HTTPException(status_code=404, detail="Is no longer available")
        
        response = product.to_dict()
        vendor_info = {}
        if product.vendor:
            vendor_info = {"vendor_name":product.vendor.name, "email":product.vendor.email, "phone":product.vendor.phone, "seller_id":product.vendor.id}
        
        response = {**response, **vendor_info}
        return response
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

@products_bp.post("/send_order")
async def send_order(product_info:CreateOrder, request:Request, db:session=Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        if not token:
            pass
        payload = decode_token(token) if token else {}
        user = db.query(Vendor).filter(Vendor.id==payload.get("id")).first()

        order_id = str(uuid4().hex)
        new_order = Orders(user_phone=user.phone if user else None,
            product_id=product_info.product_id,
            vendor_id=product_info.vendor_id,
            quantity=product_info.quantity,
            money=product_info.money,
            product_name=product_info.product_name,
            order_id=order_id
                )
        
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        
        return new_order.to_dict()
    except Exception as e:
        db.rollback()
        print(e)
        logger.exception("error occur")
        logger.exception("error occur")
        raise HTTPException(status_code=500, detail=str(e))

@products_bp.post("/upload")
async def upload_product(
    request:Request,
    product_name:str=Form(...),
    price:float=Form(...),
    market:str=Form(...),
    vendor_phone:str=Form(...),
    photo:UploadFile = File(...),
    slug:str=Form(...),
    category:str=Form(...),
    details:str=Form(...),
    db:session=Depends(get_db)
    
):
    try:
        token = request.cookies.get("access_token")
        if not token:
            logger.warning("Token not found")
            raise HTTPException(status_code=401, detail="Token not found")
        payload = decode_token(token)
        if not payload:
            logger.warning("Token not found")
            raise HTTPException(status_code=401, detail="Token not found")
        
        vendor_id = payload.get("id",)
       
        if photo.size and photo.size > MAX_LENGTH:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="File too large")
        if photo.content_type not in ALLOW_EXTENSTION:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="File Content not allow")
        
        # r2_file_upload = upload_to_r2(photo, 'posts')
        # file_url = r2_file_upload['url']
        # file_key = r2_file_upload['key']
        
        now = datetime.now()
        new_product = {'product_name':product_name, 'featured_image':'file_url', 'file_key':'file_key', 'price':price, 'vendor_phone':vendor_phone, 'market':market, 'created_at':now, "vendor_id":vendor_id, 'category':category, 'slug':slug,
        "details":details}
        
        
        new_pd = Products(**new_product)
        db.add(new_pd)
        db.commit()
        db.refresh(new_pd)
        
        return {"detail":f"Producted {new_pd.product_name} posted"}
    except Exception as e:
        db.rollback()
        logger.exception("Fail to post")
        # if r2_file_upload:
        #     try:
        #         delete_file_from_r2(r2_file_upload["key"])
        #     except Exception as delete_error:
        #         print(f"Failed to delete uploaded file: {delete_error}")
        raise HTTPException(
            status_code=500,
                detail=str(e)
            )
