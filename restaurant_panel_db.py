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
    """방문 기록 생성 후 리뷰를 저장하는 트랜잭션 함수"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. visits 테이블에 방문 기록 생성
            visit_sql = """
                INSERT INTO visits (user_id, restaurant_id, visit_date)
                VALUES (%s, %s, CURDATE())
            """
            cursor.execute(visit_sql, (user_id, restaurant_id))
            visit_id = cursor.lastrowid # 방금 생성된 visit_id 가져오기

            # 2. reviews 테이블에 리뷰 데이터 저장
            review_sql = """
                INSERT INTO reviews (visit_id, rating, content, created_at)
                VALUES (%s, %s, %s, NOW())
            """
            cursor.execute(review_sql, (visit_id, rating, content))
            
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        print(f"Review Save Error: {e}")
        return False
    finally:
        conn.close()