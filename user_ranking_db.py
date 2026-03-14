# user_ranking_db.py
from db import get_connection

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