from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session, mapped_column, Mapped
from sqlalchemy import create_engine, inspect, Table, Column, Integer, ForeignKey
from decimal import Decimal
import uuid
from dotenv import load_dotenv
from datetime import datetime, date
import os
from fastapi import Depends

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") 

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit = False
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Base(DeclarativeBase):
    pass

post_tags = Table(
    "post_tag",
    Base.metadata,
    Column("post_id", ForeignKey("posts.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True)
)
class Mixin(DeclarativeBase):
    
    def to_dict(self, exclude:list[str]|None=None)-> dict:
        
        if not exclude:
            exclude = ['']
            
        exclude = set(exclude)
            
        result = {}
        
        for col in inspect(self).mapper.column_attrs:
            name = col.key
            if name in exclude:
                continue
            value = getattr(self, name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, date):
                value = value.isoformat()
            elif isinstance(value, Decimal):
                value = float(value)
            elif isinstance(value, uuid.UUID):
                value = str(value)
            result[name] = value
        return result
    
    def update(self, update_data:dict|None=None, exclude=['featured_image', 'id', 'created_at']):
        for k, v in update_data.items():
            if k in exclude:
                print("can't change the value of ", k)
                continue
            att = getattr(self, k)
            if not att:
                continue
            setattr(self, k, v)
    
                    
        
    