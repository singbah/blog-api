from fastapi import APIRouter, HTTPException, Request, status, Depends, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session as session
import os
from datetime import datetime

from src.models import Posts, Tags
from src.database import get_db
from config import (get_user_agent, 
                    MAX_LENGTH, ALLOW_EXTENSTION,
                    decode_token, UPLOAD_FOLDER, create_slug
                    )
from config.utilities import upload_to_r2, delete_file_from_r2

posts_blue_print = APIRouter(prefix="/posts")

# GET ALL POST/BLOGS
@posts_blue_print.get("/posts")
async def get_posts(request:Request, db:session=Depends(get_db), cursor:int=Query(None), limit:int=Query(ge=20, le=20, limit=100)):
    try:
        posts = db.query(Posts).order_by(Posts.id.desc())
        int(cursor) if cursor else None
        if cursor:
            posts = posts.filter(Posts.id < cursor)
        
        posts = posts.limit(limit).all()
            
        posts = [p.to_dict('') for p in posts]
        return {
            "posts": posts,
            "last_id": posts[-1].get("id") if posts else None,
            "has_more": len(posts) == limit
        }
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

# CREATE NEW POST
@posts_blue_print.post("/create_post")
async def create_post(
    request: Request,
    title: str = Form(...),
    excert: str = Form(...),
    content: str = Form(...),
    published_at: str = Form(...),
    published_time: str = Form(...),
    tags: str = Form(...),
    photo: UploadFile = File(...),
    db: session = Depends(get_db),
):
    filename = None

    try:
        payload = decode_token(request.cookies.get("access_token"))

        if not payload or payload.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized"
            )

        slug = create_slug(title)

        if db.query(Posts).filter_by(slug=slug).first():
            raise HTTPException(
                status_code=400,
                detail="A post with this title already exists."
            )

        if photo.content_type not in ALLOW_EXTENSTION:
            raise HTTPException(
                status_code=415,
                detail="Unsupported image type."
            )


        if photo.size > MAX_LENGTH:
            raise HTTPException(
                status_code=413,
                detail="Image is too large."
            )

        file_result = upload_to_r2(photo, folder="posts")

        file_url = file_result["url"]
        file_key = file_result["key"]
        
        tag_objects = []
        for tag_name in {t.strip() for t in tags.split(",") if t.strip()}:

            slug_tag = create_slug(tag_name)

            tag = db.query(Tags).filter_by(slug=slug_tag).first()

            if not tag:
                tag = Tags(
                    name=tag_name,
                    slug=slug_tag
                )
                db.add(tag)

            tag_objects.append(tag)

        post = Posts(
            title=title,
            excert=excert,
            content=content,
            slug=slug,
            featured_image=file_url,
            file_key=file_key,
            published_at=datetime.strptime(
                published_at,
                "%Y-%m-%d"
            ),
            status="published" if published_time == "publish" else "draft",
            tags=tag_objects,
        )

        db.add(post)
        db.commit()
        db.refresh(post)

        return {
            "detail": "Post created successfully.",
            "post_id": post.id,
            "slug": post.slug,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        print(e)
        if filename:
            try:
                os.remove(
                    os.path.join(
                        UPLOAD_FOLDER, + "posts_media" + filename
                    )
                )
            except OSError:
                pass

        raise HTTPException(
            status_code=500,
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
@posts_blue_print.get("/post/{postSlug}")
async def get_post(postSlug:str, request:Request, db:session=Depends(get_db)):
    try:
        blog = db.query(Posts).filter(Posts.slug==postSlug).first()
        if not blog:
            raise HTTPException(
                status_code=404,
                detail="Blog Not Found"
            )
        post_tags = [p.to_dict() for p in blog.tags]
        # print(post_tags)
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
            
        db.delete(post)
        db.commit()
        
        delete_file_from_r2(post.file_key)
        
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
        blogs = db.query(Posts).filter(Posts.title.ilike(f"%{q}%"))
        
        blogs = [t.to_dict() for t in blogs]
        print(blogs)
        return blogs
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

# RELATED POSTS
@posts_blue_print.get("/related/{slug}")
def related_posts(slug: str, db:session= Depends(get_db)):
    try:
        post = db.query(Posts).filter(Posts.slug == slug).first()

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        # get tag ids from current post
        
        tag_ids = [t.id for t in post.tags]

        if not tag_ids:
            return []

        related = (
            db.query(Posts)
            .join(Posts.tags)
            .filter(Tags.id.in_(tag_ids))
            .filter(Posts.id != post.id)  # exclude current post
            .distinct()
            .limit(5)
            .all()
        )
        
        # print(related)

        return [p.to_dict() for p in related]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# VIEW POST
@posts_blue_print.post("/view/{slug}")
async def add_view(slug: str, db: session = Depends(get_db)):
    post = db.query(Posts).filter(Posts.slug == slug).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.views += 1

    db.commit()

    return {"detail": "View recorded"}