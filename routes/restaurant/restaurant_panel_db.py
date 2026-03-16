import os
from db import get_connection


def get_restaurant_detail(restaurant_id):
    """특정 음식점의 상세 정보와 대표 이미지를 가져오는 함수"""
    sql = """
        SELECT
            r.restaurant_id,
            r.name,
            r.description,
            r.road_address,
            r.phone,
            r.business_hours,
            r.status,
            (
                SELECT image_url
                FROM restaurant_images
                WHERE restaurant_id = r.restaurant_id
                ORDER BY sort_order ASC
                LIMIT 1
            ) AS image_url
        FROM restaurants r
        WHERE r.restaurant_id = %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (restaurant_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def get_restaurant_menus(restaurant_id):
    """특정 음식점의 메뉴 목록을 가져오는 함수"""
    sql = """
        SELECT menu_name, price
        FROM restaurant_menus
        WHERE restaurant_id = %s
        ORDER BY menu_id ASC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (restaurant_id,))
            return cursor.fetchall()
    finally:
        conn.close()


def get_restaurant_reviews(restaurant_id):
    """특정 음식점의 리뷰 목록을 가져오는 함수"""
    sql = """
        SELECT
            r.review_id,
            r.rating,
            r.content,
            r.created_at,
            u.nickname,
            u.profile_image_url AS user_image,
            v.user_id,
            GROUP_CONCAT(ri.image_url ORDER BY ri.sort_order ASC) AS review_images
        FROM reviews r
        JOIN visits v
            ON r.visit_id = v.visit_id
        JOIN users u
            ON v.user_id = u.user_id
        LEFT JOIN review_images ri
            ON r.review_id = ri.review_id
        WHERE v.restaurant_id = %s
          AND (r.status IS NULL OR r.status = 'ACTIVE')
        GROUP BY
            r.review_id,
            r.rating,
            r.content,
            r.created_at,
            u.nickname,
            u.profile_image_url,
            v.user_id
        ORDER BY r.created_at DESC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (restaurant_id,))
            return cursor.fetchall()
    finally:
        conn.close()


def save_restaurant_review(restaurant_id, user_id, rating, content, image_urls=None):
    """리뷰 저장"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            visit_sql = """
                INSERT INTO visits (user_id, restaurant_id, visited_at)
                VALUES (%s, %s, NOW())
            """
            cursor.execute(visit_sql, (user_id, restaurant_id))
            visit_id = cursor.lastrowid

            review_sql = """
                INSERT INTO reviews (visit_id, rating, content, status, created_at)
                VALUES (%s, %s, %s, 'ACTIVE', NOW())
            """
            cursor.execute(review_sql, (visit_id, rating, content))
            review_id = cursor.lastrowid

            if image_urls:
                image_sql = """
                    INSERT INTO review_images (review_id, image_url, sort_order)
                    VALUES (%s, %s, %s)
                """
                for idx, url in enumerate(image_urls):
                    cursor.execute(image_sql, (review_id, url, idx + 1))

            conn.commit()
            return True
    except Exception as e:
        print(f"save_restaurant_review 에러: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_review_transaction(review_id, user_id):
    """사용자 본인 리뷰 삭제"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            check_sql = """
                SELECT v.visit_id
                FROM reviews r
                JOIN visits v
                    ON r.visit_id = v.visit_id
                WHERE r.review_id = %s
                  AND v.user_id = %s
            """
            cursor.execute(check_sql, (review_id, user_id))
            res = cursor.fetchone()

            if not res:
                return False

            visit_id = res["visit_id"]

            cursor.execute(
                "SELECT image_url FROM review_images WHERE review_id = %s",
                (review_id,)
            )
            image_rows = cursor.fetchall()
            image_paths_to_delete = []

            for row in image_rows:
                img_url = row.get("image_url")
                if img_url:
                    image_paths_to_delete.append(img_url.lstrip("/"))

            cursor.execute(
                "DELETE FROM review_images WHERE review_id = %s",
                (review_id,)
            )
            cursor.execute(
                "DELETE FROM reviews WHERE review_id = %s",
                (review_id,)
            )
            cursor.execute(
                "DELETE FROM visits WHERE visit_id = %s",
                (visit_id,)
            )

            cursor.execute("SELECT MAX(review_image_id) AS max_id FROM review_images")
            row_img = cursor.fetchone()
            max_img_id = row_img["max_id"] if row_img["max_id"] is not None else 0
            cursor.execute(f"ALTER TABLE review_images AUTO_INCREMENT = {max_img_id + 1}")

            cursor.execute("SELECT MAX(review_id) AS max_id FROM reviews")
            row_rev = cursor.fetchone()
            max_rev_id = row_rev["max_id"] if row_rev["max_id"] is not None else 0
            cursor.execute(f"ALTER TABLE reviews AUTO_INCREMENT = {max_rev_id + 1}")

            cursor.execute("SELECT MAX(visit_id) AS max_id FROM visits")
            row_vis = cursor.fetchone()
            max_vis_id = row_vis["max_id"] if row_vis["max_id"] is not None else 0
            cursor.execute(f"ALTER TABLE visits AUTO_INCREMENT = {max_vis_id + 1}")

            conn.commit()

            for file_path in image_paths_to_delete:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as file_e:
                        print(f"⚠️ 파일 삭제 실패: {file_path} - {file_e}")

            return True

    except Exception as e:
        print(f"delete_review_transaction 에러: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()