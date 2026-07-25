
from src.routers.posts import posts_blue_print
from src.routers.auths import auths_bp
from src.routers.admins.dashboard import admin_bp
from src.routers.users.user import user_bp
from src.routers.services.products import products_bp

all_blue_prints = [posts_blue_print, auths_bp, user_bp, admin_bp, products_bp]
