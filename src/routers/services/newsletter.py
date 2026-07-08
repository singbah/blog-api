from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from src.models import Posts, NewsLetter
from src.database import SessionLocal
from config.emails import send_batch_email
from config import logger

template_dir = Path(__file__).parent.parent / "templates" / "emails"

env = Environment(
    loader=FileSystemLoader(template_dir)
)


async def send_newsletter(post_id: int):

    db = SessionLocal()

    try:

        post = db.query(Posts).filter(
            Posts.id == post_id
        ).first()

        if not post:
            return

        subscribers = db.query(NewsLetter).all()

        template = env.get_template("newsletter.html")

        emails = []

        for sub in subscribers:

            html = template.render(
                name=sub.name,
                title=post.title,
                excerpt=post.excert,
                image=post.featured_image,
                url=f"https://www.easitechlr.com/post/{post.slug}"
            )

            emails.append(
                {
                    "from": "Easi Tech Lr support@easitechlr.com",
                    "to": sub.email,
                    "subject": post.title,
                    "html": html,
                }
            )

        response = await send_batch_email(emails)
        logger.info(f"|batch emain response | {response}")
        

    finally:
        db.close()

