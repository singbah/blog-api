from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import time, asyncio
from sqlalchemy.orm import Session as ses

from src.models import Vendor, OTP
from src.database import get_db
# from config.emails import send_email

from config import (create_token, logger, decode_token, NOW, 
                    MAX_ATTEMPT, ACCOUNT_LOCK_DELAY, check_password, set_hash_password)
from src.schemas import UserLogin, CreateUser

auths_bp = APIRouter(prefix="/api/auths")

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
            samesite='lax',
            httponly=True,
            secure=True,
            max_age=60*60*24*7,
            path="/"
        )
        # REFRESH TOKEN
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            samesite='lax',
            httponly=True,
            secure=True,
            max_age=60*60*24*7,
            path="/"
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
                samesite="lax")
            
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
                    "role": user.role
                }
            )

        new_refresh_token = create_token(
                {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role
                },
                exps=60 * 60 * 24 * 7
            )
        
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            samesite='lax',
            httponly=True,
            secure=True,
            max_age=3600*24*7,
            path="/"
        )
        
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            samesite='lax',
            httponly=True,
            secure=True,
            max_age=3600*24*7,
            path="/"
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
        samesite="lax"
        )
        response.delete_cookie(
        key="refresh_token",
        secure=True,
        samesite="lax"
        )
        return {"detail":"you are logout"}
    except Exception as e:
        logger.exception("Something went wrong on refresh")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@auths_bp.post("/forgot_password")
async def forgot_password(email:str, request:Request, db:ses=Depends(get_db)):
    try:
        if not email:
            raise HTTPException(status_code=404, detail="You Didn't send email")
        
        user = db.query(Vendor).where(Vendor.email == email).first()
        ip_address = request.client.host if request.client else "None"
        if not user:
            logger.warning(f"User with IP {ip_address} Fail Account Recovery with email {email}")
            raise HTTPException(status_code=401, detail=f"This email {email} is not associated with any account here.")
        
        otp = uuid4().hex[0:6]
        
        user = {"email":user.email, "name":user.name, "otp":otp}
        now = datetime.now()
        new_opt = OTP(
            code=otp, email=email, created_at=now, expires_at=now + timedelta(minutes=5)
        )
        db.add(new_opt)
        db.commit()
        db.refresh(new_opt)
        
        # await send_email(recipients=email, template_name="account_recovery.html", context={"otp":otp, "name":user.name}, subject="Account recovery")
        
        return new_opt.to_dict()
    except Exception as e:
        db.rollback()
        logger.exception("error occur")
        raise HTTPException(status_code=500, detail=str(e))

@auths_bp.get("/confirm_opt")
async def confirm_opt_code(otp:str, email:str, request:Request,response:Response, db:ses=Depends(get_db)):#
    try:
        ip_address = request.client.host if request.client else "None"
        now = datetime.now(timezone.utc)
        
        user = db.query(Vendor).filter(Vendor.email==email).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"user with email {email} dosn't exist.")
        
        if user.is_block:
            logger.warning(f"disabled account {email} try account recovery | ip {ip_address}")
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="This account is disabled")
        
        code = db.query(OTP).filter(OTP.email==email).where(OTP.code==otp).order_by(OTP.created_at.desc()).first()
        if not code:
            logger.warning("Incorrect code")
            raise HTTPException(status_code=404, detail="OTP not found")
        
        if code.expires_at and code.expires_at <= now:
            logger.warning(f"user {email} retry expried OTP IP {ip_address}")
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail="OTP EXPIRED, REQUEST NEW ONE.") 
        
        if code.is_used:
            logger.warning(f"User {email} retry used OTP| IP {ip_address}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Token already used")       
        
        code.is_used = True
        user.updated_at = now
        user.last_login = now
        user.account_locck_delay = None
        user.max_attempt = 0
        db.commit()
        
        new_access_token = create_token(
            {
                "id": user.id,
                "email": user.email,
                "role": user.role
            }
        )

        new_refresh_token = create_token(
            {
                "id": user.id,
                "email": user.email,
                "role": user.role
            },
            exps=60 * 60 * 24 * 7
        )
        
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            samesite="lax",
            httponly=True,
            secure=True,
            path="/",
            max_age=60*60*24*7,
        )
        
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            samesite="lax",
            httponly=True,
            secure=True,
            max_age=60*60*24*7,
        )
        
        return user.to_dict()
    
    except Exception as e:
        db.rollback()
        logger.exception("error occur")
        print(str(e))
        raise HTTPException(status_code=500, detail=str(e))      

@auths_bp.get("/password-reset")
async def password_reset(new_password:str, email:str, request:Request, db:ses=Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        payload = decode_token(token)
        
        if not token:
            logger.warning("No token No access")
            raise HTTPException(status_code=401, detail="An error occur")
        
        if not email:
            raise HTTPException(status_code=404, detail="user not found")
        
        user = db.query(Vendor).filter(Vendor.email==email).first()
        if not user:
            raise HTTPException(status_code=404, detail="Couldn't find user")
        
        hash_pwd = set_hash_password(new_password)
        user.hash_password = hash_pwd
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        
        return {'detail':"Password changed"}
    except Exception as e:
        db.rollback()
        logger.exception("error occur")
        raise HTTPException(status_code=500, detail=str(e))
