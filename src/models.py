from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from src.database import Base, Mixin, post_tags

class Admin(Base, Mixin):
    __tablename__ = 'admins'
    
    id:Mapped[int] = mapped_column(primary_key=True)
    username:Mapped[str] = mapped_column(nullable=False)
    email:Mapped[str] = mapped_column(nullable=False)
    phone:Mapped[str]
    role:Mapped[str] = mapped_column(default="admin")
    password:Mapped[str] = mapped_column(nullable=False)
    max_att:Mapped[int] = mapped_column(default=0, nullable=True)
    account_lock_delay:Mapped[datetime] = mapped_column(default=None, nullable=True)
    last_login:Mapped[datetime] = mapped_column(nullable=True)
    created_at:Mapped[datetime] = mapped_column(default=datetime.now())
    updated_at:Mapped[datetime] = mapped_column(default=datetime.now())
    
class BlockIPAddresses(Base, Mixin):
    __tablename__ = 'blocked_ip_addresses'
    
    id:Mapped[int] = mapped_column(primary_key=True)
    phone:Mapped[str] = mapped_column(nullable=False)
    ip_address:Mapped[str] = mapped_column(nullable=False)
    user_agent:Mapped[str] = mapped_column(nullable=False)
    end_point:Mapped[str] = mapped_column(nullable=False)
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))

class Setting(Base, Mixin):
    __tablename__ = 'settings'
    id:Mapped[int] = mapped_column(primary_key=True)
    key:Mapped[str] = mapped_column(unique=True, nullable=False)
    value:Mapped[str]
    type:Mapped[str] = mapped_column(default='text')
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))

class NewsletterCampign(Base, Mixin):
    __tablename__ = "newsletter_campign"
    
    id:Mapped[int] = mapped_column(primary_key=True)
    post_id:Mapped[int] = mapped_column(nullable=False)
    status:Mapped[str] = mapped_column(default="newsletter")
    sent:Mapped[bool] = mapped_column(nullable=False)
    faid:Mapped[bool] = mapped_column(nullable=False)
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    
class ContactMessage(Base, Mixin):
    __tablename__= "contact_messages"
    id:Mapped[int] = mapped_column(primary_key=True)
    name:Mapped[str] = mapped_column(nullable=False)
    email:Mapped[str] = mapped_column(nullable=False)
    ip_address:Mapped[str]
    source:Mapped[str] 
    message:Mapped[str] = mapped_column(nullable=False)
    subject:Mapped[str] = mapped_column(nullable=False)
    status:Mapped[str] = mapped_column(default="new", nullable=True)
    user_agent:Mapped[str] = mapped_column(nullable=True)
    newsletter:Mapped[bool] = mapped_column(default=False)
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    
class Posts(Base, Mixin):
    __tablename__='posts'
    
    id:Mapped[int] = mapped_column(primary_key=True)
    title:Mapped[str] = mapped_column(nullable=False)
    slug:Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    excert:Mapped[str] = mapped_column(nullable=False)
    content:Mapped[str] = mapped_column(nullable=False)
    author:Mapped[str]
    featured_image:Mapped[str]
    file_key:Mapped[str] = mapped_column(nullable=True)
    status:Mapped[bool] = mapped_column(default=True)
    views:Mapped[int] = mapped_column(default=0)
    tags:Mapped[list['Tags']]=relationship(secondary=post_tags, back_populates='posts')
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    published_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))

class Comments(Base, Mixin):
    __tablename__="comments"
    
    id:Mapped[int] = mapped_column(primary_key=True)
    post_id:Mapped[int] = mapped_column(nullable=False)
    comment:Mapped[str] = mapped_column(nullable=False)
    user_email:Mapped[str] = mapped_column(nullable=True, default=None)
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))

class NewsLetter(Base, Mixin):
    __tablename__ = 'news_letters'
    
    id:Mapped[int] = mapped_column(primary_key=True)
    name:Mapped[str]
    email:Mapped[str] = mapped_column(unique=True, nullable=False)
    status:Mapped[str] = mapped_column(default='subscribed')
    source:Mapped[str]
    last_open:Mapped[datetime] = mapped_column(default=datetime.now(), nullable=True)
    ip_address:Mapped[str]
    user_agent:Mapped[str] = mapped_column(default=None)
    created_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at:Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
 
class Tags(Base, Mixin):
    __tablename__ = 'tags'

    id:Mapped[int] = mapped_column(primary_key=True)
    name:Mapped[str] = mapped_column(nullable=False, unique=True)
    slug:Mapped[str] = mapped_column(nullable=False, unique=True)
    description:Mapped[str] = mapped_column(nullable=True)
    posts:Mapped[list['Posts']] = relationship(secondary=post_tags, back_populates='tags')
    created_at:Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now(timezone.utc)
    )

class SiteVisit(Base):
    __tablename__ = "site_visits"

    id: Mapped[int] = mapped_column(primary_key=True)

    path: Mapped[str]
    ip_address: Mapped[str] 
    user_agent: Mapped[str] 
    referer: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc))