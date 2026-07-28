from fastapi import APIRouter, Request, Response, HTTPException, status, Depends, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as session
from src.models import Products
from src.database import get_db
from datetime import datetime, timedelta
import os
from uuid import uuid4
from config import ALLOW_EXTENSTION, MAX_ATTEMPT, MAX_LENGTH, logger, decode_token
from config.utilities import upload_to_r2

products_bp = APIRouter(prefix="/products", tags=["Products BluePrint"])

@products_bp.get("/listings")
async def get_listings(request:Request, cursor:int=Query(default=0), limit:int=Query(le=20, limit=100), db:session=Depends(get_db)):
    try:
        products = db.query(Products).where(Products.id > cursor).order_by(Products.created_at.desc()).limit(limit)
        
        
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
        return response
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@products_bp.post("/upload")
async def upload_product(
    request:Request,
    product_name:str=Form(...),
    price:int=Form(...),
    market:str=Form(...),
    vendor_phone:str=Form(...),
    photo:UploadFile = File(...),
    slug:str=Form(...),
    category:str=Form(...),
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
        
        # file_name = str(uuid4().hex) + '.jpeg'
        
        r2_file_upload = upload_to_r2(photo, 'posts')
        file_url = r2_file_upload['url']
        file_key = r2_file_upload['key']
        
        now = datetime.now()
        # created_at = now
        new_product = {'product_name':product_name, 'featured_image':file_url, 'file_key':file_key, 'price':price, 'vendor_phone':vendor_phone, 'market':market, 'created_at':now, "vendor_id":vendor_id, 'category':category, 'slug':slug}
        
        
        new_pd = Products(**new_product)
        db.add(new_pd)
        db.commit()
        db.refresh(new_pd)
        
        return new_pd.to_dict()
    except Exception as e:
        db.rollback()
        logger.exception("Fail to post")
        if r2_file_upload:
            try:
                delete_file_from_r2(r2_file_upload["key"])
            except Exception as delete_error:
                print(f"Failed to delete uploaded file: {delete_error}")
        raise HTTPException(
            status_code=500,
                detail=str(e)
            )
