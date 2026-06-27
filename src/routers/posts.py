from fastapi import APIRouter, HTTPException, Response, Request, status, Depends, UploadFile, File, Form, Query
from sqlalchemy.orm import Session as session
import os
from uuid import uuid4
from datetime import datetime, timedelta

from src.models import Posts, Tags
from src.database import get_db
from config import (get_user_agent, 
                    MAX_LENGTH, ALLOW_EXTENSTION,
                    delete_file, decode_token, UPLOAD_FOLDER, create_slug
                    )

posts_blue_print = APIRouter(prefix="/posts")

# GET ALL POST/BLOGS
@posts_blue_print.get("/posts")
async def get_posts(request:Request, db:session=Depends(get_db)):
    try:
        user_agent_str = request.headers.get("user-agent")
        ua = get_user_agent(user_agent_str)
        ip_address = request.client.host

        posts = db.query(Posts).order_by(Posts.created_at.desc()).limit(100)
        posts = [p.to_dict('') for p in posts]
        
        return posts
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# GET ALL TAGS
@posts_blue_print.get("/tags")
async def get_tags(request:Request, db:session=Depends(get_db)):
    try:
        user_agent_str = request.headers.get("user-agent")
        ua = get_user_agent(user_agent_str)
        ip_address = request.client.host

        tags = db.query(Tags).order_by(Tags.created_at.desc()).limit(100)
        tags = [p.to_dict('') for p in tags]
        
        return tags
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ADD NEW POST
@posts_blue_print.post("/posts")
async def post_blog(
    response:Response, 
    request:Request,
    title:str = Form(...),
    excert:str=Form(...),
    content:str=Form(...),
    photo:UploadFile=File(...),
    db:session=Depends(get_db)
    ):
    try:
        
        user_agent_str = request.headers.get("user-agent")
        
        ua = get_user_agent(user_agent_str)
        ip_address = request.client.host
        
        payload = decode_token(request.cookies.get("access_token"))
        if not payload or payload.get("role") != 'admin':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized attempt"
            )
        
        if photo.content_type not in ALLOW_EXTENSTION:
            print("File extenstion not validid")
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="file content not allow"
            )
        elif photo.size > MAX_LENGTH:
            print("File Size too large")
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="File too large"
            )
            
        file_content = await photo.read()
        filename = f'{uuid4().hex}.{photo.filename.split(".")[-1]}' 
        
        upload_folder = os.path.join(UPLOAD_FOLDER, "posts_media")
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file_url = f"/posts_media/{filename}"
        
        with open(file_path, 'wb') as fd:
            fd.write(file_content)
        
        slug = create_slug(title)
        now = datetime.utcnow()
        new_post = Posts(
            title=title, excert=excert, content=content, 
            featured_image=file_url, slug=slug, published_at=now + timedelta(hours=1), status='schedule'
        )
        db.add(new_post)
        db.commit()
        db.flush(new_post)
        
        print(new_post.tags)
        return new_post.to_dict()

    except Exception as e:
        print(e)
        await delete_file('featured_image')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# EDIT POST 
@posts_blue_print.patch("/edit")
async def edit_post(edit_data:dict, request:Request, db:session=Depends(get_db)):
    try:
        payload = decode_token(request.cookies.get("access_token"))
        if not payload:
            raise HTTPException(
                status_code=401,
                detail='action not allowed'
            )
        
        blog = db.query(Posts).filter(Posts.id==edit_data.get("id")).first()
        
        if not blog:
            raise HTTPException(
                status_code=404,
                detail="Blog/Post not found"
            )
        
        blog.update(edit_data)
        db.commit()

        return blog.to_dict()
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

# GET A POST
@posts_blue_print.get("/post")
async def get_post(post_id:int, request:Request, db:session=Depends(get_db)):
    try:
        blog = db.query(Posts).filter(Posts.id==post_id).first()
        if not blog:
            raise HTTPException(
                status_code=404,
                detail="Blog Not Found"
            )
        
        for d in blog.tags:
            print(d.to_dict())
        return blog.to_dict()
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
# GET A TAG
@posts_blue_print.get("tag")
async def get_tag(tag_id:int, request:Request, db:session=Depends(get_db)):
    try:
        tag = db.query(Tags).filter(Tags.id==tag_id).first()
        if not tag:
            raise HTTPException(
                status_code=404,
                detail="tag Not Found"
            )
        
        for d in tag.tags:
            print(d.to_dict())
        return tag.to_dict()
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
@posts_blue_print.delete("/delete")
async def delete_post(post_id:int, request:Request, db:session=Depends(get_db)):
    try:
        payload = decode_token(request.cookies.get("access_token"))
        if not payload or payload.get("role") != 'admin':
            raise HTTPException(
                status_code=401, 
                detail="Action not allowed"
            )
        
        post = db.query(Posts).filter(Posts.id==post_id).first()
        if not post:
            raise HTTPException(
                status_code=404,
                detail="Post not found"
            )
            
        photo_url = post.featured_image
        db.delete(post)
        db.commit()
        
        await delete_file(photo_url)
      
            
        
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

# ADD TAGS
@posts_blue_print.post("/search/tag")
async def search_tag(request:Request, tag_info:dict, db:session=Depends(get_db)):
    try:
        post_id = tag_info.get("post_id")
        post = db.query(Posts).filter(Posts.id==post_id).first()
        
        if not post:
            raise HTTPException(
                status_code=404,
                detail=f"Blog with id {post_id} not found"
            )
        
        tags = []
        for t in tag_info.get("data"):
            t_slug = create_slug(t)
            if db.query(Tags).filter(Tags.slug==t_slug).first():
              continue
            
            new_tags = Tags(name=t, slug=t_slug)
            db.add(new_tags)
            db.commit()
            tags.append(new_tags)
        
        
        post.tags = tags
        db.commit()
    
        return {"detail":"Tag is live"}
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

# SEARCH POST/BLOG
@posts_blue_print.get("/search/blog")
async def search_blog(q:str, request:Request, db:session=Depends(get_db)):
    try:
        tags = db.query(Posts).filter(Posts.title.ilike(f"%{q}%"))
        
        tags = [t.to_dict() for t in tags]
        return tags
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
