import os
import uuid
import pymysql
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from PIL import Image  
load_dotenv()



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

#====================================================================================
# owner_board_management.html
#-------------------------------------------------------------------------------------
