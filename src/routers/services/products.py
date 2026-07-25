from fastapi import APIRouter, Request, Response, HTTPException, status, Depends, Query, UploadFile, File, Form
from sqlalchemy.orm import Session as session
from datetime import datetime, timedelta
import os
from uuid import uuid4
from save_json import save_t_json, read_json_file

products_bp = APIRouter(prefix="/products", tags=["Products BluePrint"])

@products_bp.get("/listings")
async def get_listings(request:Request, cursor:int=Query(default=0), limit:int=Query(le=20, limit=100)):
    try:
        products = read_json_file()
        
        response = {"listings":products, "cursor":0, "limit":20}
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@products_bp.post("/upload")
async def upload_product(
    product_name:str=Form(...),
    price:int=Form(...),
    market:str=Form(...),
    vendor_phone:str=Form(...),
    photo:UploadFile = File(...)
):
    try:
        content = await photo.read()
        
        upload_folder = os.path.join(os.getcwd(), "static", "products")
       
        
        os.makedirs(upload_folder, exist_ok=True)
        filetype = photo.content_type.split("/")[-1] if photo.content_type else '.png'
        filename = str(uuid4().hex) + f'.{filetype}'
        filepath = os.path.join(upload_folder, filename)
        file_url = f"/products/{filename}"
        
        new_product = {'product_name':product_name, 'photo':file_url, 'price':price, 'vendor_phone':vendor_phone, 'market':market}
        
        # with open(filepath, "wb") as fd:
        #     fd.write(content)
        
        save_t_json(new_product)
        
        
        return{"detail":f"filename -> {file_url}"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
