from fastapi import APIRouter, Response, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session as session
from src.models import Posts
from src.database import get_db

sitemap_bp = APIRouter()


@sitemap_bp.get("/sitemap.xml", response_class=PlainTextResponse)
def get_sitemap(db:session=Depends(get_db)):
    base_url = 'https://www.easitechlr.com'
    
    urls = [
        f'{base_url}/',
        f'{base_url}/blog',
        f'{base_url}/contact',
        f'{base_url}/about',
    ]
    
    
    posts = db.query(Posts).all()
    
    for p in posts:
        urls.append(f"{base_url}/{p.slug}")
    xml_items = ''.join([f'<url><loc>{u}</loc><url>' for u in urls])
        
    # print(xml_items)
    xml = f"""<?xml version = "1.0" encoing="UTF-8"?> 
        <urlset xml = "http://www.sitemaps.org/schemas/sitemap/0.9">
        {xml_items}
        </urlset>
        """
    return Response(content=xml, media_type='application/xml')
    