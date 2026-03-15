import os
import uuid
import pymysql
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from PIL import Image  
# Python Imaging Library로 이미지 열기/저장, 크기 변경, 
# 포맷 변환(JPG ↔ PNG ↔ WEBP), 썸네일 작성(비율 유지 축소) 등 작업 가능
load_dotenv()

# owner 메뉴 이미지 저장 경로 추가
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(BASE_DIR)
MENU_IMAGE_DIR = os.path.join(PROJECT_DIR, "static" , "img", "owner")
MENU_THUMB_DIR = os.path.join(MENU_IMAGE_DIR, "thumbs")
ALLOWED_EXT = {"jpg", "jpeg", "png", "gif", "webp"}
THUMB_MAX_SIZE = (240, 240)

os.makedirs(MENU_IMAGE_DIR, exist_ok=True)
os.makedirs(MENU_THUMB_DIR, exist_ok=True)


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
# owner_menu_management.html
#-------------------------------------------------------------------------------------
#-------------------------------------------------------------------------------------
# 이미지 파일 처리 - menu_management
#-------------------------------------------------------------------------------------

# 업로드 허용 확장자 검사 함수 추가
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


# static 기준 상대경로 생성 함수 추가
def build_menu_image_rel_path(stored_name):
    return f"img/owner/{stored_name}"


def build_menu_thumb_rel_path(stored_name):
    return f"img/owner/thumbs/{stored_name}"


# 썸네일 생성 함수 추가
def make_thumbnail(src_abs, thumb_abs):
    ext = os.path.splitext(thumb_abs)[1].lower()

    with Image.open(src_abs) as image:
        image.thumbnail(THUMB_MAX_SIZE)

        if ext in [".jpg", ".jpeg"]:
            if image.mode in ("RGBA", "LA"):
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.getchannel("A"))
                image = background
            elif image.mode == "P":
                image = image.convert("RGBA")
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.getchannel("A"))
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            image.save(thumb_abs, format="JPEG", quality=90)
        else:
            image.save(thumb_abs)


#  업로드 파일 저장 + 썸네일 생성 + DB 저장용 메타데이터 반환
def save_menu_image_file(image_file):
    raw_name = (image_file.filename or "").strip()

    if not raw_name or "." not in raw_name:
        raise ValueError("확장자가 있는 이미지 파일만 업로드할 수 있습니다.")

    ext = raw_name.rsplit(".", 1)[1].lower()

    if ext not in ALLOWED_EXT:
        raise ValueError("허용되지 않은 이미지 확장자입니다.")

    original_name = raw_name
    stored_name = f"{uuid.uuid4().hex}.{ext}"

    image_abs_path = os.path.join(MENU_IMAGE_DIR, stored_name)
    thumb_abs_path = os.path.join(MENU_THUMB_DIR, stored_name)

    image_file.save(image_abs_path)
    make_thumbnail(image_abs_path, thumb_abs_path)

    return {
        "original_name": original_name,
        "stored_name": stored_name,
        "image_url": build_menu_image_rel_path(stored_name),
        "thumb_url": build_menu_thumb_rel_path(stored_name)
    }

# 실제 파일 삭제 안전 처리
def safe_remove_file(rel_path):
    if not rel_path:
        return

    abs_path = os.path.join(PROJECT_DIR, "static", rel_path)

    try:
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except Exception:
        pass

# restaurant_images에서 menu_id 기준 대표 이미지 1건 조회 
def get_menu_image_by_menu_id(cursor, restaurant_id, menu_id):
    sql = """
        SELECT
            image_id,
            restaurant_id,
            menu_id,
            image_url,
            thumb_url,
            original_name,
            stored_name,
            sort_order,
            created_at
        FROM restaurant_images
        WHERE restaurant_id = %s
        AND menu_id = %s
        ORDER BY sort_order ASC, image_id ASC
        LIMIT 1
    """
    cursor.execute(sql, (restaurant_id, menu_id))
    return cursor.fetchone()


# restaurant_images insert 함수 추가
def insert_menu_image(cursor, restaurant_id, menu_id, image_data, sort_order=1):
    sql = """
        INSERT INTO restaurant_images
        (
            restaurant_id,
            menu_id,
            image_url,
            thumb_url,
            original_name,
            stored_name,
            sort_order
        )
        VALUES
        (
            %s, %s, %s, %s, %s, %s, %s
        )
    """
    cursor.execute(
        sql,
        (
            restaurant_id,
            menu_id,
            image_data["image_url"],
            image_data["thumb_url"],
            image_data["original_name"],
            image_data["stored_name"],
            sort_order
        )
    )

# restaurant_images update 함수 추가
def update_menu_image(cursor, image_id, image_data):
    sql = """
        UPDATE restaurant_images
        SET
            image_url = %s,
            thumb_url = %s,
            original_name = %s,
            stored_name = %s
        WHERE image_id = %s
    """
    cursor.execute(
        sql,
        (
            image_data["image_url"],
            image_data["thumb_url"],
            image_data["original_name"],
            image_data["stored_name"],
            image_id
        )
    )

# restaurant_images delete 함수 추가
def delete_menu_image_by_menu_id(cursor, restaurant_id, menu_id):
    current_image = get_menu_image_by_menu_id(cursor, restaurant_id, menu_id)

    if current_image:
        safe_remove_file(current_image.get("image_url"))
        safe_remove_file(current_image.get("thumb_url"))

        sql = """
            DELETE FROM restaurant_images
            WHERE restaurant_id = %s
            AND menu_id = %s
        """
        cursor.execute(sql, (restaurant_id, menu_id))


def get_owner_info(owner_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT owner_id, owner_name, email, status
                FROM owners
                WHERE owner_id = %s
                LIMIT 1
            """
            cursor.execute(sql, (owner_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def get_restaurant_id_by_owner(owner_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT restaurant_id, name, status
                FROM restaurants
                WHERE owner_id = %s
                LIMIT 1
            """
            cursor.execute(sql, (owner_id,))
            return cursor.fetchone()
    finally:
        conn.close()

# -------------------------------------------------------------------------------------
# 메뉴 카테고리 조회
# -------------------------------------------------------------------------------------
def get_menu_categories():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT menu_category_id, menu_category_name
                FROM menu_categories
                ORDER BY menu_category_id ASC
            """
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()

#------------------------------------------------------------------------------------
# 등록된 메뉴 출력 (페이징)- menu_management
#------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------
# 등록된 메뉴 목록 조회
# -------------------------------------------------------------------------------------
def get_menu_list_by_owner(owner_id, limit=None, offset=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT
                    rm.menu_id,
                    rm.menu_name,
                    rm.price,
                    rm.status,
                    mc.menu_category_name,
                    ri.image_url,
                    ri.thumb_url,
                    ri.original_name
                FROM restaurant_menus rm
                INNER JOIN restaurants r
                    ON rm.restaurant_id = r.restaurant_id
                LEFT JOIN menu_categories mc
                    ON rm.menu_category_id = mc.menu_category_id
                LEFT JOIN restaurant_images ri
                    ON ri.restaurant_id = rm.restaurant_id
                    AND ri.menu_id = rm.menu_id
                    AND ri.image_id = (
                        SELECT image_id
                        FROM restaurant_images
                        WHERE restaurant_id = rm.restaurant_id
                        AND menu_id = rm.menu_id
                        ORDER BY sort_order ASC, image_id ASC
                        LIMIT 1
                    )
                WHERE r.owner_id = %s
                ORDER BY rm.menu_id DESC
            """

            params = [owner_id]

            if limit is not None and offset is not None:
                sql += " LIMIT %s OFFSET %s"
                params.extend([limit, offset])

            cursor.execute(sql, tuple(params))
            return cursor.fetchall()
    finally:
        conn.close()


# -------------------------------------------------------------------------------------
# 등록된 메뉴 총 개수 조회
# -------------------------------------------------------------------------------------
def get_menu_count_by_owner(owner_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT COUNT(*) AS cnt
                FROM restaurant_menus rm
                INNER JOIN restaurants r
                    ON rm.restaurant_id = r.restaurant_id
                WHERE r.owner_id = %s
            """
            cursor.execute(sql, (owner_id,))
            row = cursor.fetchone()
            return row["cnt"] if row else 0
    finally:
        conn.close()


# -------------------------------------------------------------------------------------
# 메뉴 상세 조회
# -------------------------------------------------------------------------------------
def get_menu_detail_by_id(owner_id, menu_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT
                    rm.menu_id,
                    rm.restaurant_id,
                    rm.menu_category_id,
                    rm.menu_name,
                    rm.price,
                    rm.status,
                    ri.image_url,
                    ri.thumb_url,
                    ri.original_name,
                    ri.stored_name
                FROM restaurant_menus rm
                INNER JOIN restaurants r
                    ON rm.restaurant_id = r.restaurant_id
                LEFT JOIN restaurant_images ri
                    ON ri.restaurant_id = rm.restaurant_id
                    AND ri.menu_id = rm.menu_id
                    AND ri.image_id = (
                        SELECT image_id
                        FROM restaurant_images
                        WHERE restaurant_id = rm.restaurant_id
                        AND menu_id = rm.menu_id
                        ORDER BY sort_order ASC, image_id ASC
                        LIMIT 1
                    )
                WHERE r.owner_id = %s
                AND rm.menu_id = %s
                LIMIT 1
            """
            cursor.execute(sql, (owner_id, menu_id))
            return cursor.fetchone()
    finally:
        conn.close()

#------------------------------------------------------------------------------------
# 메뉴 등록 (insert) - menu_management
#------------------------------------------------------------------------------------

def insert_menu(owner_id, menu_category_id, menu_name, price, status, image_file=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            restaurant = get_restaurant_id_by_owner(owner_id)
            if not restaurant:
                raise ValueError("해당 owner의 restaurant가 없습니다.")

            restaurant_id = restaurant["restaurant_id"]

            sql = """
                INSERT INTO restaurant_menus
                (
                    restaurant_id,
                    menu_category_id,
                    menu_name,
                    price,
                    status
                )
                VALUES
                (
                    %s, %s, %s, %s, %s
                )
            """
            cursor.execute(
                sql,
                (
                    restaurant_id,
                    menu_category_id,
                    menu_name,
                    price,
                    status
                )
            )

            menu_id = cursor.lastrowid

            if image_file and image_file.filename:
                image_data = save_menu_image_file(image_file)
                insert_menu_image(
                    cursor=cursor,
                    restaurant_id=restaurant_id,
                    menu_id=menu_id,
                    image_data=image_data,
                    sort_order=1
                )

            conn.commit()
            return menu_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def update_menu(owner_id, menu_id, menu_category_id, menu_name, price, status, image_file=None, remove_image=False):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            restaurant = get_restaurant_id_by_owner(owner_id)
            if not restaurant:
                raise ValueError("해당 owner의 restaurant가 없습니다.")

            restaurant_id = restaurant["restaurant_id"]

            sql = """
                UPDATE restaurant_menus rm
                INNER JOIN restaurants r
                    ON rm.restaurant_id = r.restaurant_id
                SET
                    rm.menu_category_id = %s,
                    rm.menu_name = %s,
                    rm.price = %s,
                    rm.status = %s
                WHERE r.owner_id = %s
                AND rm.menu_id = %s
                AND rm.restaurant_id = %s
            """
            cursor.execute(
                sql,
                (
                    menu_category_id,
                    menu_name,
                    price,
                    status,
                    owner_id,
                    menu_id,
                    restaurant_id
                )
            )

            # 현재 "이미지" 조회 후 수정/삭제 처리하도록 정리
            current_image = get_menu_image_by_menu_id(cursor, restaurant_id, menu_id)

            # 수정 화면에서 "이미지" 삭제 체크만 해도 기존 파일과 DB row를 함께 지우도록 추가
            if remove_image:
                delete_menu_image_by_menu_id(cursor, restaurant_id, menu_id)
                current_image = None

            if image_file and image_file.filename:
                image_data = save_menu_image_file(image_file)

                if current_image:
                    safe_remove_file(current_image.get("image_url"))
                    safe_remove_file(current_image.get("thumb_url"))
                    update_menu_image(cursor, current_image["image_id"], image_data)
                else:
                    insert_menu_image(
                        cursor=cursor,
                        restaurant_id=restaurant_id,
                        menu_id=menu_id,
                        image_data=image_data,
                        sort_order=1
                    )

            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
#------------------------------------------------------------------------------------
# 메뉴 삭제 (DELETE) - menu_management
#------------------------------------------------------------------------------------
# 실제 삭제 처리
def delete_menu(owner_id, menu_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            restaurant = get_restaurant_id_by_owner(owner_id)
            if not restaurant:
                raise ValueError("해당 owner의 restaurant가 없습니다.")

            restaurant_id = restaurant["restaurant_id"]

            delete_menu_image_by_menu_id(cursor, restaurant_id, menu_id)

            sql = """
                DELETE rm
                FROM restaurant_menus rm
                INNER JOIN restaurants r
                    ON rm.restaurant_id = r.restaurant_id
                WHERE r.owner_id = %s
                AND rm.menu_id = %s
                AND rm.restaurant_id = %s
            """
            cursor.execute(sql, (owner_id, menu_id, restaurant_id))

            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()