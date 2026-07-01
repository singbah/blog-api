from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session as ses
import re, os
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
import user_agents
from uuid import uuid4 as uid
import unicodedata, re



load_dotenv()

PWD_CONTENT = CryptContext(schemes=['argon2'], deprecated='auto')
ALGORITHM = os.getenv("ALGORITHM")
APP_KEY = os.getenv("APP_KEY")

NOW  = datetime.now()

UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "upload")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MAX_LENGTH = 1024*1024*20
ALLOW_EXTENSTION = {'image/jpeg', 'image/png', 'image/jpg', 'video/mp4', 'video/od'}

MAX_ATTEMPT = 5
IP_BLOCK_ATTEMPT = 5
UUID = uid().hex
ACCOUNT_LOCK_DELAY = NOW + timedelta(minutes=1)

# APPLY IP BLOCK
# def block_supecious_ip(ip_address:str, user_agent, end_point, db:None):
#     attempt = IP_BLOCK_ATTEMPT
    
#     attempt -= 1
#     if IP_BLOCK_ATTEMPT-1 <= 0:
#         new_block_ip = BlockIPAddresses(
#             ip_address=ip_address,
#             user_agent=user_agent, 
#             end_point=end_point
#         )
#         db.add(new_block_ip)
#         db.commit()
#         db.flush(new_block_ip)
#         return {"detail":"This ip is block"}
        
    
# CREATE TOKEN
def create_token(user_data:dict, exps=60*60*5):
    try:
        exp = NOW + timedelta(seconds=exps)
        user_data.update({"exp":exp})
        
        token = jwt.encode(user_data, key=APP_KEY, algorithm=ALGORITHM)
        return token
    except Exception as e:
        print(str(e))
        return str(e)

# DECODE TOKEN
def decode_token(token)->dict:
    try:
        payload = jwt.decode(token, key=APP_KEY, algorithms=ALGORITHM)
        return payload
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# DELETE A FILE FROM DIRECTORY
async def delete_file(file_url):
    try:
        file_to_delete = os.path.join(UPLOAD_FOLDER + file_url)
        if not os.path.exists(file_to_delete):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='File not found in directory'
            )
        print(file_to_delete, 'is deleted')
        os.remove(file_to_delete)
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# FIND FILE
async def find_file(file_url):
    file_found = os.path.join(UPLOAD_FOLDER + file_url)
    if not file_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="file not found in directory"
        )
    
    return file_found

# HASH PASSWORD
def hash_password(password:str):
    try:
        hash_pwd = PWD_CONTENT.hash(password.encode())
        return hash_pwd
    except Exception as e:
        return(str(e))

# CHECK HASHED PASSWORD AND VALIDATE
def check_password(plain:str, hash_pwd):
    try:
        return PWD_CONTENT.verify(plain, hash_pwd)
    except Exception as e:
        print(e)
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

def get_user_agent(user_agent_string):
    ua = user_agents.parse(user_agent_string)
    return {
        "browser": {
            "family": ua.browser.family,
            "version": ua.browser.version_string,
        },
        "os": {
            "family": ua.os.family,
            "version": ua.os.version_string,
        },
        "device": {
            "family": ua.device.family,
            "brand": ua.device.brand,
            "model": ua.device.model,
        },
        "is_mobile": ua.is_mobile,
        "is_tablet": ua.is_tablet,
        "is_pc": ua.is_pc,
        "is_bot": ua.is_bot,
    }

def create_slug(title:str):
    if not title:
        return "untitled"
    
    slug = unicodedata.normalize("NFKD", title,).encode("ascii", "ignore").decode("ascii")

    slug = slug.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    
    slug = slug.strip("-")
    slug = re.sub(r'-{2}', "-", slug)
    
    return slug or "untitled"

def schedule_format(date_str):
    today_date = NOW.date()
    time_ = NOW.time()
    print(date_str)    