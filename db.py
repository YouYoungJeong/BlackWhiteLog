import os
import pymysql
from dotenv import load_dotenv

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

    # status 컬럼 값이 정확히 어떤 enum인지 명세 일부만 보여서
    # 운영 데이터에 따라 OPEN / ACTIVE 등으로 바꿔도 됨.
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
                row["image_url"] = row["image_url"] or "https://placehold.co/160x120?text=No+Image"
                row["avg_rating"] = float(row["avg_rating"] or 0)
                row["visit_count"] = int(row["visit_count"] or 0)
                row["review_count"] = int(row["review_count"] or 0)

            return rows
    finally:
        conn.close()