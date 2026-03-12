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