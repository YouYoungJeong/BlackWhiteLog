from db import get_connection

####
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
####