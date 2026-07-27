from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from datetime import datetime, timedelta
import time
from sqlalchemy.orm import Session as ses

from src.models import Vendor
from src.database import get_db
from config import logger
from config import (get_user_agent, create_token, decode_token, NOW, 
                    MAX_ATTEMPT, ACCOUNT_LOCK_DELAY, check_password, set_hash_password)
from src.schemas import UserLogin, CreateUser

auths_bp = APIRouter(prefix="/auths")

@auths_bp.post("/signup")
async def vendor_signup(user_data:CreateUser, db:ses=Depends(get_db)):
    try:
        hash_password = set_hash_password(user_data.password)
        
        existing_user = db.query(Vendor).where(Vendor.phone==user_data.phone).first()
        
        if existing_user:
            logger.warning(f"user already exist with phone {user_data.phone}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This user already exist")
        
        new_vendor = Vendor(
            name=user_data.name,
            phone=user_data.phone,
            hash_password=hash_password,
            email=user_data.email
        )
        db.add(new_vendor)
        db.commit()
        return {"detail":"Your account is created on Liberia biggest marketplace add product now as a vendor and receive order right in your whatsapp dm."}
    except Exception as e:
        db.rollback()
        logger.exception("error occur")
        raise HTTPException(status_code=500, detail=str(e))
    
@auths_bp.post("/signin")
async def vendor_signin(login_data:UserLogin, request:Request, response:Response, db:ses=Depends(get_db)):
    try:
        now = datetime.now()
        user = db.query(Vendor).where(Vendor.phone == login_data.phone).first()
        ip_address = ''
        if request.client:
            ip_address = request.client.host
        if not user:
            raise HTTPException(status_code=500, detail="User not found")
        if user.is_block:
            logger.warning("Block account try loging in")
            raise HTTPException(status_code=423, detail="This account is block please contact...")
        
        if user.account_locck_delay and user.account_locck_delay > now:
            remain_time = now - user.account_locck_delay 
            logger.warning(f"This account is log for {remain_time.seconds}")
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=f"This account is lock for {remain_time.seconds} seconds")
        
        if not check_password(login_data.password, user.hash_password):
            user.max_attempt += 1
            if user.max_attempt >= MAX_ATTEMPT:
                user.account_locck_delay = now + timedelta(minutes=5)
            user.updated_at = now
            db.commit()
            raise HTTPException(status_code=401, detail="Wrong Credentail")
        
        user.max_attempt = 0
        user.account_locck_delay = None
        user.updated_at = now
        user.last_login = now
        db.commit()
        user_data = {
            'id':user.id,
            'email':user.email,
            'role':user.role
        }
        access_token = create_token(user_data=user_data)
        refresh_token = create_token(user_data=user_data, exps=60*60*60*24*7)
        
        # CREATE ACCESS TOKEN
        response.set_cookie(
            key="access_token",
            value=access_token,
            secure=True, 
            samesite='none',
            httponly=True,
            # partitioned=True
        )
        # REFRESH TOKEN
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            secure=True, 
            samesite='none',
            httponly=True,
            # partitioned=True
        )
        logger.info(f"vonder {user.email} logged in from {ip_address}")
        return user.to_dict()
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))    

@auths_bp.post('/refresh')
async def refresh(request:Request, response:Response, db:ses=Depends(get_db)):
    try:
        token = request.cookies.get("refresh_token")
        
        if not token:
            logger.warning("No token on refresh")
            raise HTTPException(
                status_code=401,
                detail="Token not found"
            )
            
        payload = decode_token(token)
        if not payload:
            logger.exception("No payload on refresh")
            raise HTTPException(
                status_code=400,
                detail='an error occur'
            )
        user = db.query(Vendor).filter(Vendor.id==payload.get("id")).first()
        if not user:
            response.delete_cookie(
                key="access_token",
                secure=True,
                samesite="none")
            
            logger.warning("user not found")
            raise HTTPException(
                status_code=401,
                detail="user not found"
            )
        if user.is_block:
            response.delete_cookie(
                key="access_token",
                secure=True,
                samesite="none")
            raise HTTPException(status_code=401, detail="This user is block")
        
        new_access_token = create_token(
                {
                    "id": user.id,
                    "email": user.email,
                    "role": "user"
                }
            )

        new_refresh_token = create_token(
                {
                    "id": user.id,
                    "email": user.email,
                    "role": "user"
                },
                exps=60 * 60 * 24 * 7
            )
        
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            samesite="none",
            httponly=True,
            secure=True,
        )
        
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            samesite="none",
            httponly=True,
            secure=True
        )
        
        return user.to_dict()
    except HTTPException:
        raise

    except Exception:
        logger.exception("Refresh token error")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@auths_bp.post("/logout")
async def logout(response:Response, request:Request):
    try:     
        response.delete_cookie(
        key="access_token",
        secure=True,
        samesite="none"
        )
        response.delete_cookie(
        key="refresh_token",
        secure=True,
        samesite="none"
        )
        return {"detail":"you are logout"}
    except Exception as e:
        logger.exception("Something went wrong on refresh")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    