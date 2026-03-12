import os
import pymysql
from dotenv import load_dotenv

# 비밀번호 해시 생성 / 비밀번호 검사용
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "heukbaeklog"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def fetch_regions():
    sql = """
        SELECT DISTINCT region_sigungu
        FROM restaurants
        WHERE region_sigungu IS NOT NULL
        AND region_sigungu <> ''
        ORDER BY region_sigungu ASC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [row["region_sigungu"] for row in rows]
    finally:
        conn.close()


def fetch_categories():
    sql = """
        SELECT restaurant_category_id, restaurant_category_name
        FROM restaurant_categories
        ORDER BY restaurant_category_name ASC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()


def fetch_restaurants(region=None, keyword=None, category_id=None, sort_by="visits"):
    """
    sort_by:
      - visits   : 방문수순
      - rating   : 평점순
      - reviews  : 리뷰많은순
      - latest   : 최신등록순
    """

    order_by_map = {
        "visits": "visit_count DESC, avg_rating DESC, review_count DESC, r.created_at DESC",
        "rating": "avg_rating DESC, review_count DESC, visit_count DESC, r.created_at DESC",
        "reviews": "review_count DESC, avg_rating DESC, visit_count DESC, r.created_at DESC",
        "latest": "r.created_at DESC, visit_count DESC, avg_rating DESC",
    }

    order_by = order_by_map.get(sort_by, order_by_map["visits"])

    sql = f"""
        SELECT
            r.restaurant_id,
            r.name,
            r.address,
            r.road_address,
            r.latitude,
            r.longitude,
            r.phone,
            r.business_hours,
            r.description,
            r.region_sido,
            r.region_sigungu,
            r.region_dong,
            r.status,
            r.created_at,
            rc.restaurant_category_name AS category_name,

            COALESCE(vs.visit_count, 0) AS visit_count,
            COALESCE(rv.review_count, 0) AS review_count,
            COALESCE(rv.avg_rating, 0) AS avg_rating,

            (
                SELECT COALESCE(ri.thumb_url, ri.image_url)
                FROM restaurant_images ri
                WHERE ri.restaurant_id = r.restaurant_id
                ORDER BY ri.sort_order ASC, ri.image_id ASC
                LIMIT 1
            ) AS image_url

        FROM restaurants r
        LEFT JOIN restaurant_categories rc
            ON r.restaurant_category_id = rc.restaurant_category_id

        LEFT JOIN (
            SELECT restaurant_id, COUNT(*) AS visit_count
            FROM visits
            GROUP BY restaurant_id
        ) vs
            ON r.restaurant_id = vs.restaurant_id

        LEFT JOIN (
            SELECT
                v.restaurant_id,
                COUNT(rv.review_id) AS review_count,
                ROUND(AVG(rv.rating), 1) AS avg_rating
            FROM reviews rv
            INNER JOIN visits v
                ON rv.visit_id = v.visit_id
            GROUP BY v.restaurant_id
        ) rv
            ON r.restaurant_id = rv.restaurant_id

        WHERE 1=1
    """

    params = []

    # 운영 가능한 음식점만 보이게 하는 조건
    # 실제 DB 상태값이 다르면 OPEN / ACTIVE 부분은 맞게 수정하면 됨
    sql += " AND (r.status IS NULL OR r.status IN ('OPEN', 'ACTIVE')) "

    if region and region != "전체":
        sql += " AND r.region_sigungu = %s "
        params.append(region)

    if keyword:
        sql += """
            AND (
                r.name LIKE %s
                OR r.address LIKE %s
                OR r.road_address LIKE %s
                OR r.description LIKE %s
                OR rc.restaurant_category_name LIKE %s
            )
        """
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword] * 5)

    if category_id and str(category_id).strip():
        sql += " AND r.restaurant_category_id = %s "
        params.append(category_id)

    sql += f" ORDER BY {order_by} LIMIT 100 "

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            for row in rows:
                # 이미지가 없으면 기본 이미지 사용
                row["image_url"] = row["image_url"] or "https://placehold.co/160x120?text=No+Image"
                row["avg_rating"] = float(row["avg_rating"] or 0)
                row["visit_count"] = int(row["visit_count"] or 0)
                row["review_count"] = int(row["review_count"] or 0)

            return rows
    finally:
        conn.close()


# -----------------------------
# 로그인 관련 함수
# -----------------------------
def verify_user_login(email, password):
    sql = """
        SELECT *
        FROM users
        WHERE email = %s
        AND (status IS NULL OR status <> 'DELETED')   -- 탈퇴 회원 제외
        LIMIT 1
    """

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user["password_hash"], password):
                return user
            else:
                return None
    finally:
        conn.close()


# -----------------------------
# 이메일 중복 확인 함수 (추가)
# -----------------------------
def find_user_by_email(email):
    sql = """
        SELECT user_id, email, nickname, status
        FROM users
        WHERE email = %s
        LIMIT 1
        """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (email,))
            return cursor.fetchone()
    finally:
        conn.close()


# -----------------------------
# 회원가입 함수
# -----------------------------
def create_user(nickname, email, password):
    """
    회원가입 시 비밀번호를 해시로 변환해서 저장
    실제 DB 컬럼명은 password가 아니라 password_hash
    """

    conn = get_connection()

    # 입력받은 비밀번호를 안전하게 해시 처리
    password_hash = generate_password_hash(password)

    sql = """
        INSERT INTO users (email, password_hash, nickname)
        VALUES (%s, %s, %s)
    """

    try:
        with conn.cursor() as cursor:
            # 컬럼 순서: email, password_hash, nickname
            cursor.execute(sql, (email, password_hash, nickname))
        conn.commit()
    finally:
        conn.close()

        # -----------------------------
# 카카오/소셜 로그인용 사용자 조회
# -----------------------------
def find_user_by_social(provider, social_id):
    sql = """
        SELECT *
        FROM users
        WHERE provider = %s
        AND social_id = %s
        AND (status IS NULL OR status <> 'DELETED')   -- 탈퇴 회원 제외
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (provider, social_id))
            return cursor.fetchone()
    finally:
        conn.close()


# -----------------------------
# 카카오/소셜 로그인용 사용자 생성
# -----------------------------
def create_social_user(nickname, email, provider, social_id, profile_image_url=None):
    sql = """
        INSERT INTO users (nickname, email, password_hash, provider, social_id, profile_image_url)
        VALUES (%s, %s, NULL, %s, %s, %s)
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (nickname, email, provider, social_id, profile_image_url))
        conn.commit()
    finally:
        conn.close()


def create_social_user(nickname, email, provider, social_id, profile_image_url=None):
    sql = """
        INSERT INTO users (nickname, email, password_hash, provider, social_id, profile_image_url)
        VALUES (%s, %s, NULL, %s, %s, %s)
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (nickname, email, provider, social_id, profile_image_url))
        conn.commit()
    finally:
        conn.close()

def withdraw_user(user_id):
    sql = """
        UPDATE users
        SET status = 'DELETED'
        WHERE user_id = %s
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id,))
        conn.commit()
    finally:
        conn.close()

def restore_user(user_id):
    sql = """
        UPDATE users
        SET status = 'ACTIVE'
        WHERE user_id = %s
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id,))
        conn.commit()
    finally:
        conn.close()