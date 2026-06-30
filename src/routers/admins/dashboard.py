from fastapi import APIRouter, Request, Response, HTTPException, status
from src.models import *
from sqlalchemy.orm import Session as sec


admin_bp = APIRouter(prefix="/admin")

