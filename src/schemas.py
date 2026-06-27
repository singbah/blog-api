from pydantic import EmailStr, BaseModel
from fastapi import Depends, Form, File, UploadFile
from typing import Optional

class CreatePost(BaseModel):
    title:str=Form(...)
    excert:str=Form(...)
    content:str=Form(...)

class CreateLead(BaseModel):
    email:str
    name:str
    tags:str

class CreateInquiries(BaseModel):
    name:str
    email:str
    phone:str
    subject:str
    message:str
    service_type:str
    budget_type:str

class AdminLogin(BaseModel):
    password:str
    phone:str |None

def as_form(title, excert, content) ->CreatePost:
    return CreatePost(title=title, content=content, excert=excert)