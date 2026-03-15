import os
from db import get_connection, is_favorite_restaurant

def get_restaurant_detail(restaurant_id, user_id=None):
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
            row = cursor.fetchone()

            if not row:
                return None

            row["is_favorite"] = False
            if user_id:
                row["is_favorite"] = is_favorite_restaurant(user_id, restaurant_id)

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
        
def save_restaurant_review(restaurant_id, user_id, rating, content, image_urls=None):
    """
    visits는 필수 외래키만, reviews는 created_at 포함하여 저장
    """

    from db import get_connection
    # 티어 업데이트 함수를 안에서 임포트 (순환 참조 방지)
    from routes.ranking.user_ranking_db import check_and_update_tier

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
            review_id = cursor.lastrowid  # 방금 생성된 리뷰 ID 가져오기
            
            # 3. review_images 테이블 삽입 (이미지가 있을 경우)
            if image_urls:
                image_sql = """
                    INSERT INTO review_images (review_id, image_url, sort_order)
                    VALUES (%s, %s, %s)
                """
                for idx, url in enumerate(image_urls):
                    # 명세서에 따라 원본 이미지 경로(image_url)와 출력 순서(sort_order) 저장
                    cursor.execute(image_sql, (review_id, url, idx + 1))

            conn.commit()

        # [변경] 미션 처리 (일일 리뷰 달성 50점) - 여기서 중복을 걸러냅니다!
        from routes.ranking.user_ranking_db import process_mission, check_and_update_tier 
        
        # 하루 첫 리뷰 50점 지급 시도
        process_mission(user_id, 'DAILY_REVIEW', 50, is_weekly=False)

        # 티어 검사 실행
        check_and_update_tier(user_id)
        return True
    
    except Exception as e:
        conn.rollback()
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

            # 2. 삭제할 이미지 경로 미리 조회 (DB 지우기 전에 백업)
            cursor.execute("SELECT image_url FROM review_images WHERE review_id = %s", (review_id,))
            image_rows = cursor.fetchall()
            image_paths_to_delete = []
            
            for row in image_rows:
                img_url = row.get('image_url')
                if img_url:
                    # DB에는 '/static/img/...' 로 저장되어 있으므로 앞의 '/'를 제거하여 실제 상대 경로로 변환
                    file_path = img_url.lstrip('/')
                    image_paths_to_delete.append(file_path)
            
            # 리뷰이미지 아이디 데이터 삭제
            cursor.execute("DELETE FROM review_images WHERE review_id = %s", (review_id,))
            # 리뷰 삭제
            cursor.execute("DELETE FROM reviews WHERE review_id = %s", (review_id,))
            # 방문기록 삭제
            cursor.execute("DELETE FROM visits WHERE visit_id = %s", (visit_id,))
            
            # review_images 테이블 초기화
            cursor.execute("SELECT MAX(review_image_id) AS max_id FROM review_images")
            row_img = cursor.fetchone()
            max_img_id = row_img['max_id'] if row_img['max_id'] is not None else 0
            cursor.execute(f"ALTER TABLE review_images AUTO_INCREMENT = {max_img_id + 1}")
            # reviews 테이블 AUTO_INCREMENT 초기화
            cursor.execute("SELECT MAX(review_id) AS max_id FROM reviews")
            row_rev = cursor.fetchone()
            max_rev_id = row_rev['max_id'] if row_rev['max_id'] is not None else 0
            cursor.execute(f"ALTER TABLE reviews AUTO_INCREMENT = {max_rev_id + 1}")
            # visits 테이블 AUTO_INCREMENT 초기화
            cursor.execute("SELECT MAX(visit_id) AS max_id FROM visits")
            row_vis = cursor.fetchone()
            max_vis_id = row_vis['max_id'] if row_vis['max_id'] is not None else 0
            cursor.execute(f"ALTER TABLE visits AUTO_INCREMENT = {max_vis_id + 1}")

            conn.commit()
            
            # 물리적 이미지 파일 삭제 (DB 삭제가 완벽히 성공한 후에만 실행)
            for file_path in image_paths_to_delete:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as file_e:
                        print(f"⚠️ 파일 삭제 권한 없음/실패: {file_path} - {file_e}")
            
            return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()