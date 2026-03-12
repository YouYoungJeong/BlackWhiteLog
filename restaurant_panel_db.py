from db import get_connection

def get_restaurant_detail(restaurant_id):
    """특정 음식점의 상세 정보와 대표 이미지를 가져오는 함수"""
    # 수정된 SQL: 서브쿼리를 사용하여 첫 번째(sort_order 최우선) 이미지 URL을 가져옵니다.
    sql = """
        SELECT r.restaurant_id, r.name, r.description, r.road_address, 
                r.phone, r.business_hours, r.status,
                (SELECT image_url FROM restaurant_images 
                WHERE restaurant_id = r.restaurant_id 
                ORDER BY sort_order ASC LIMIT 1) AS image_url
        FROM restaurants r
        WHERE r.restaurant_id = %s
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (restaurant_id,))
            row = cursor.fetchone()
            # 임시 이미지 할당 로직 삭제됨 (DB에서 바로 가져옴)
            return row
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
    """특정 음식점의 리뷰(댓글) 목록을 가져오는 함수"""
    # reviews, visits, users, review_image 4개 테이블 조인
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
        JOIN visits v ON r.visit_id = v.visit_id
        JOIN users u ON v.user_id = u.user_id
        LEFT JOIN review_images ri ON r.review_id = ri.review_id
        WHERE v.restaurant_id = %s
        GROUP BY r.review_id
        ORDER BY r.created_at DESC
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (restaurant_id,))
            return cursor.fetchall()
    finally:
        conn.close()
        
def save_restaurant_review(restaurant_id, user_id, rating, content):
    """
    [명세서 준수] visits는 필수 외래키만, reviews는 created_at 포함하여 저장
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. visits 테이블 (visit_date 에러가 났었으므로, 필수 정보만 입력)
            # 만약 DB에서 자동 생성이 안 된다면 명세서대로 'visit_date'를 다시 확인해야 해!
            visit_sql = """
                INSERT INTO visits (user_id, restaurant_id, visited_at)
                VALUES (%s, %s, NOW())
            """
            cursor.execute(visit_sql, (user_id, restaurant_id))
            visit_id = cursor.lastrowid 

            # 2. reviews 테이블 (명세서의 created_at 컬럼 사용)
            review_sql = """
                INSERT INTO reviews (visit_id, rating, content, created_at)
                VALUES (%s, %s, %s, NOW())
            """
            cursor.execute(review_sql, (visit_id, rating, content))
            
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"Review Save Error (DB): {e}")
        return False
    finally:
        conn.close()

def delete_review_transaction(review_id, user_id):
    """리뷰 삭제 및 AUTO_INCREMENT 정리"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 소유권 확인 및 visit_id 추출
            check_sql = """
                SELECT v.visit_id FROM reviews r 
                JOIN visits v ON r.visit_id = v.visit_id 
                WHERE r.review_id = %s AND v.user_id = %s
            """
            cursor.execute(check_sql,(review_id, user_id))
            res = cursor.fetchone()
            if not res: return False # 소유권 없음

            visit_id = res['visit_id']

            # 2. 자식(리뷰) 삭제
            cursor.execute("DELETE FROM reviews WHERE review_id = %s", (review_id,))
            
            # 3. 부모(방문기록) 삭제
            cursor.execute("DELETE FROM visits WHERE visit_id = %s", (visit_id,))

            # # 4. AUTO_INCREMENT 최적화 
            # # 마지막 번호를 지웠을 때 다음 번호가 건너뛰지 않도록 현재 최대값으로 조정
            # cursor.execute("SELECT MAX(review_id) AS max_id FROM reviews")
            # max_id = cursor.fetchone()['max_id'] or 0
            # cursor.execute(f"ALTER TABLE reviews AUTO_INCREMENT = {max_id + 1}")
            
            # 3. reviews 테이블 AUTO_INCREMENT 초기화
            cursor.execute("SELECT MAX(review_id) AS max_id FROM reviews")
            row_rev = cursor.fetchone()
            max_rev_id = row_rev['max_id'] if row_rev['max_id'] is not None else 0
            cursor.execute(f"ALTER TABLE reviews AUTO_INCREMENT = {max_rev_id + 1}")

            # 4. 🌟 visits 테이블 AUTO_INCREMENT 초기화 (추가됨)
            cursor.execute("SELECT MAX(visit_id) AS max_id FROM visits")
            row_vis = cursor.fetchone()
            max_vis_id = row_vis['max_id'] if row_vis['max_id'] is not None else 0
            cursor.execute(f"ALTER TABLE visits AUTO_INCREMENT = {max_vis_id + 1}")

            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"Delete Error: {e}")
        return False
    finally:
        conn.close()