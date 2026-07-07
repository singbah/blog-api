from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session as ses
import resend
from datetime import datetime, timedelta
from jose import jwt, ExpiredSignatureError
from passlib.context import CryptContext
from dotenv import load_dotenv
import user_agents
from uuid import uuid4 as uid
import re, unicodedata, re, os, logging
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

load_dotenv()

PWD_CONTENT = CryptContext(schemes=['argon2'], deprecated='auto')
ALGORITHM = os.getenv("ALGORITHM")
APP_KEY = os.getenv("APP_KEY")

NOW  = datetime.now()

MAX_LENGTH = 1024*1024*20
ALLOW_EXTENSTION = {'image/jpeg', 'image/png', 'image/jpg', 'video/mp4', 'video/od'}

MAX_ATTEMPT = 5
IP_BLOCK_ATTEMPT = 5
UUID = uid().hex
ACCOUNT_LOCK_DELAY = NOW + timedelta(minutes=1)

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logger = logging.getLogger("easitechlr")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler(
        log_dir / "server.log", encoding="utf-8"
    )
    
    fomatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
    file_handler.setFormatter(fomatter)
    logger.addHandler(file_handler)


template_dir = Path(__file__).parent.parent / "templates" / "emails"

env = Environment(
    loader=FileSystemLoader(template_dir)
)

resend.api_key = os.getenv("RESEND_EMAIL_API_KEY")

async def send_email(
    recipients: list[str],
    subject: str,
    template_name: str,
    context: dict,
):

    template = env.get_template(template_name)

    html = template.render(**context)

    resend.Emails.send({
        "from": "Easi Tech Lr support@easitech.email",
        "to": recipients,
        "subject": subject,
        "html": html,
    })

# CREATE TOKEN
def create_token(user_data:dict, exps=60*60*5):
    try:
        exp = datetime.now() + timedelta(seconds=exps)
        payload = user_data.copy()
        payload["exp"] = exp
        
        token = jwt.encode(payload, key=APP_KEY, algorithm=ALGORITHM)
        return token
    except Exception as e:
        logger.exception("Failed to create JWT")
        raise

# DECODE TOKEN
def decode_token(token)->dict:
    try:
        payload = jwt.decode(token, key=APP_KEY, algorithms=ALGORITHM)
        return payload
    except ExpiredSignatureError:
        logger.exception("Token has expired")
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )

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

# GET USER AGENT
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

# GENERATE SLUG
def create_slug(title:str):
    if not title:
        return "untitled"
    
    slug = unicodedata.normalize("NFKD", title,).encode("ascii", "ignore").decode("ascii")

    slug = slug.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    
    slug = slug.strip("-")
    slug = re.sub(r'-{2}', "-", slug)
    
    return slug or "untitled"

