from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from datetime import datetime, timedelta
from sqlalchemy.orm import Session as ses

from src.models import Admin
from src.database import get_db
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
        
        admin = db.query(Admin).filter(Admin.phone==phone).first()
        
        if not admin:
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not Authorized"
            )
        
        if admin.account_lock_delay and admin.account_lock_delay > NOW:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Your account is temporarily lock for {(admin.account_lock_delay - NOW)}"
            )
        
        if logdata.password != admin.password:
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
            samesite='None',
            httponly=True,
            partitioned=True
        )
        # REFRESH TOKEN
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            secure=True, 
            samesite='None',
            httponly=True,
            partitioned=True
        )
        
        return admin.to_dict()
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 

@auths_bp.post('/refresh')
async def refresh(request:Request, response:Response, db:ses=Depends(get_db)):
    try:
        token = request.cookies.get("access_token")
        
        if not token:
            raise HTTPException(
                status_code=401,
                detail="You are already logout"
            )
            
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=400,
                detail='an error occur'
            )
        admin = db.query(Admin).filter(Admin.id==payload.get("id")).first()
        
        payload['exp'] = NOW + timedelta(days=7)
        
        new_access_token = create_token(payload)
        
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            samesite="none",
            httponly=True,
            secure=True,
            partitioned=True
        )
        
        # print(admin.to_dict())
        return admin.to_dict()
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

@auths_bp.post("/logout")
async def logout(response:Response, request:Request):
    try:     
        # response.delete_cookie()
        request.cookies.clear()
        return {"detail":"you are logout"}
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    