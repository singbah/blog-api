from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from datetime import datetime, timedelta
from sqlalchemy.orm import Session as ses

from src.models import Admin, BlockIPAddresses
from src.database import get_db
from config import logger
from config import (get_user_agent, create_token, decode_token, NOW, 
                    MAX_ATTEMPT, ACCOUNT_LOCK_DELAY, check_password, hash_password)
from src.schemas import AdminLogin

auths_bp = APIRouter(prefix="/auths")

@auths_bp.post("/login")
async def login(logdata:AdminLogin, request:Request, response:Response, db:ses=Depends(get_db)):
    try:
        phone = logdata.phone
        ua = get_user_agent(request.headers.get("user-agent"))
        ip_address = request.client.host
        
        if db.query(BlockIPAddresses).filter(BlockIPAddresses.phone==phone).first():
            logger.warning(f"Invalid login attempt | Phone: {phone} | IP: {ip_address}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorization attempt"
            )
        
        
        admin = db.query(Admin).filter(Admin.phone==phone).first()
        
        if not admin:
            logger.warning(f"Invalid login attempt | Phone: {phone} | IP: {ip_address}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not Authorized"
            )
        
        if admin.account_lock_delay and admin.account_lock_delay > NOW:
            logger.warning(f"Invalid login attempt | Phone: {phone} | IP: {ip_address}")
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Your account is temporarily lock for {(admin.account_lock_delay - NOW)}"
            )
        
        if not check_password(logdata.password, admin.password):
            logger.warning(f"Failed login | Phone: {phone} | IP: {ip_address}")
            admin.max_att += 1
            if admin.max_att >= MAX_ATTEMPT:
                admin.account_lock_delay = ACCOUNT_LOCK_DELAY
            admin.updated_at = NOW
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Wrong Password"
            )
        
        
        admin.max_att = 0
        admin.account_lock_delay = None
        admin.updated_at = NOW
        admin.last_login = NOW
        db.commit()
        user_data = {
            'id':admin.id,
            'email':admin.email,
            'role':'admin'
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
        logger.info(f"Admin {admin.email} logged in from {ip_address}")
        return admin.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 

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
        admin = db.query(Admin).filter(Admin.id==payload.get("id")).first()
        if not admin:
            logger.warning("admin not found")
            raise HTTPException(
                status_code=401,
                detail="Admin not found"
            )
        
        new_access_token = create_token(
                {
                    "id": admin.id,
                    "email": admin.email,
                    "role": "admin"
                }
            )

        new_refresh_token = create_token(
                {
                    "id": admin.id,
                    "email": admin.email,
                    "role": "admin"
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
        
        return admin.to_dict()
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
        return {"detail":"you are logout"}
    except Exception as e:
        logger.exception("Something went wrong on refresh")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    