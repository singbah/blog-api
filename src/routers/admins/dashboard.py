from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from src.database import get_db
from src.models import *
from sqlalchemy.orm import Session as ses


admin_bp = APIRouter(prefix="/admin")

@admin_bp.get("/contacts")
async def get_contact(request:Request, db:ses=Depends(get_db)):
    try:
        contacts = db.query(ContactMessage).all()
        return [contact.to_dict() for contact in contacts]
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    