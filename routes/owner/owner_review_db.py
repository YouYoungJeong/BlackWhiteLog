import os
import uuid
import pymysql
from dotenv import load_dotenv
from PIL import Image


load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))

NOTICE_IMAGE_DIR = os.path.join(PROJECT_DIR, "static", "img", "owner_notic_img")
NOTICE_THUMB_DIR = os.path.join(PROJECT_DIR, "static", "img", "owner_notic_img", "thumbs")

os.makedirs(NOTICE_IMAGE_DIR, exist_ok=True)
os.makedirs(NOTICE_THUMB_DIR, exist_ok=True)

ALLOWED_EXT = {"jpg", "jpeg", "png", "gif", "webp"}
THUMB_MAX_SIZE = (300, 300)


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database="bwlog",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False
    )


# ====================================================================================
# owner_review_management.html
# ====================================================================================


