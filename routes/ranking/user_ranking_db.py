# user_ranking_db.py
from db import get_connection

TIER_THRESHOLDS = {
    'BRONZE': 0,
    'SILVER': 500,
    'GOLD': 1500,
    'PLATINUM': 3000,
    'DIAMOND': 6000
}

def get_all_user_rankings():
    """전체 유저 랭킹 리스트 (점수순)"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # SQL 실행 전, DB에 users 테이블과 아래 컬럼들이 있는지 꼭 확인하세요!
            sql = """
                SELECT user_id, nickname, point, tier, profile_image_url 
                FROM users 
                ORDER BY point DESC
            """
            cursor.execute(sql)
            return cursor.fetchall()
    except Exception as e:
        print(f"❌ DB Error (get_all_user_rankings): {e}")
        return []
    finally:
        conn.close()

def get_user_dashboard_data(user_id):
    """특정 유저 상세 데이터"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE user_id = %s"
            cursor.execute(sql, (user_id,))
            return cursor.fetchone()
    except Exception as e:
        print(f"❌ DB Error (get_user_dashboard_data): {e}")
        return None
    finally:
        conn.close()

def get_user_achievements_data(user_id):
    """전체 업적 목록과 특정 유저가 획득한 업적 목록을 반환"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 모든 업적 목록
            cursor.execute("SELECT achievement_id, name, icon_url FROM achievements")
            all_achievements = cursor.fetchall()

            # 2. 유저가 획득한 업적 목록
            cursor.execute("""
                SELECT a.achievement_id, a.name, a.icon_url 
                FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.achievement_id
                WHERE ua.user_id = %s
            """, (user_id,))
            user_achievements = cursor.fetchall()

            return {
                "all_achievements": all_achievements,
                "user_achievements": user_achievements
            }
    except Exception as e:
        print(f"❌ DB Error (get_user_achievements_data): {e}")
        return {"all_achievements": [], "user_achievements": []}
    finally:
        conn.close()

def get_ranking_summary(user_id):
    """랭킹 요약 카드용 데이터 (게이지, 방문수, 내 랭킹, 최근 뱃지) 반환"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 내 포인트 조회 (게이지 렌더링 및 등수 계산용)
            cursor.execute("SELECT point FROM users WHERE user_id = %s", (user_id,))
            user_info = cursor.fetchone()
            my_point = user_info['point'] if user_info and user_info['point'] else 0

            # 2. 방문 도장 개수 (visits 테이블에서 내 user_id 카운트)
            cursor.execute("SELECT COUNT(*) AS visit_count FROM visits WHERE user_id = %s", (user_id,))
            visit_count = cursor.fetchone()['visit_count']

            # 3. 내 랭킹 (나보다 점수가 높은 사람의 수 + 1)
            cursor.execute("SELECT COUNT(*) + 1 AS my_rank FROM users WHERE point > %s", (my_point,))
            my_rank = cursor.fetchone()['my_rank']

            # 4. 최근 획득 뱃지 이미지 (시간순 내림차순 정렬 후 1개 추출)
            cursor.execute("""
                SELECT a.icon_url 
                FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.achievement_id
                WHERE ua.user_id = %s
                ORDER BY ua.earned_at DESC, ua.user_achievement_id DESC
                LIMIT 1
            """, (user_id,))
            latest_badge_row = cursor.fetchone()
            latest_badge_img = latest_badge_row['icon_url'] if latest_badge_row else None

            return {
                "point": my_point,
                "visit_count": visit_count,
                "my_rank": my_rank,
                "latest_badge_img": latest_badge_img
            }
    except Exception as e:
        print(f"❌ DB Error (get_ranking_summary): {e}")
        return None
    finally:
        conn.close()

def check_and_update_tier(user_id):
    """
    유저의 현재 점수를 확인하고, 기준점을 넘었으면 티어를 승급(DB 업데이트)시키는 함수
    (나중에 점수가 부여되는 액션이 발생할 때마다 호출할 예정입니다.)
    """
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 1. 유저의 현재 점수와 티어 확인
            cursor.execute("SELECT point, tier FROM users WHERE user_id = %s", (user_id,))
            user_info = cursor.fetchone()
            if not user_info:
                return False

            current_point = user_info['point'] or 0
            current_tier = user_info['tier'] or 'BRONZE'

            # 2. 점수에 따른 새로운 랭크(티어) 계산
            new_tier = 'BRONZE'
            if current_point >= TIER_THRESHOLDS['DIAMOND']:
                new_tier = 'DIAMOND'
            elif current_point >= TIER_THRESHOLDS['PLATINUM']:
                new_tier = 'PLATINUM'
            elif current_point >= TIER_THRESHOLDS['GOLD']:
                new_tier = 'GOLD'
            elif current_point >= TIER_THRESHOLDS['SILVER']:
                new_tier = 'SILVER'

            # 3. 만약 새로 달성한 티어가 기존 티어와 다르면 DB 업데이트
            if new_tier != current_tier:
                cursor.execute("UPDATE users SET tier = %s WHERE user_id = %s", (new_tier, user_id))
                conn.commit()
                return True # 승급이 발생했음을 반환 (나중에 축하 알림창 띄우기 용도)
            
            return False # 승급하지 않음
    except Exception as e:
        conn.rollback()
        print(f"❌ DB Error (check_and_update_tier): {e}")
        return False
    finally:
        conn.close()