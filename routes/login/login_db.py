from db import get_connection
from werkzeug.security import generate_password_hash, check_password_hash

# =========================
# 일반 로그인 검증
# =========================
def verify_user_login(email, password):
    sql = """
        SELECT *
        FROM users
        WHERE email = %s
          AND (status IS NULL OR status <> 'DELETED')
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user["password_hash"], password):
                return user
            return None
    finally:
        conn.close()


# =========================
# 이메일로 회원 조회
# =========================
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


# =========================
# 닉네임으로 회원 조회
# =========================
def find_user_by_nickname(nickname):
    sql = """
        SELECT user_id, email, nickname, status
        FROM users
        WHERE nickname = %s
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (nickname,))
            return cursor.fetchone()
    finally:
        conn.close()


# =========================
# 일반 회원가입
# =========================
def create_user(nickname, email, password):
    password_hash = generate_password_hash(password)

    sql = """
        INSERT INTO users (email, password_hash, nickname, role)
        VALUES (%s, %s, %s, 'USER')
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (email, password_hash, nickname))
        conn.commit()
    finally:
        conn.close()


# =========================
# 소셜 로그인용 사용자 조회
# provider + social_id 기준 조회
# =========================
def find_user_by_social(provider, social_id):
    sql = """
        SELECT
            u.user_id,
            u.email,
            u.nickname,
            u.profile_image_url,
            u.status,
            u.role,
            usa.provider,
            usa.provider_user_id
        FROM user_social_accounts usa
        INNER JOIN users u
            ON usa.user_id = u.user_id
        WHERE usa.provider = %s
          AND usa.provider_user_id = %s
          AND (u.status IS NULL OR u.status <> 'DELETED')
        LIMIT 1
    """

    provider = provider.upper()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (provider, social_id))
            return cursor.fetchone()
    finally:
        conn.close()



# # =========================
# # 소셜 회원 생성
# # =========================
# def create_social_user(nickname, email, provider, social_id, profile_image_url=None):
#     provider = provider.upper()

#     user_sql = """
#         INSERT INTO users (email, password_hash, nickname, profile_image_url)
#         VALUES (%s, NULL, %s, %s)
#     """

#     social_sql = """
#         INSERT INTO user_social_accounts (user_id, provider, provider_user_id)
#         VALUES (%s, %s, %s)
#     """

#     conn = get_connection()
#     try:
#         with conn.cursor() as cursor:
#             cursor.execute(user_sql, (email, nickname, profile_image_url))
#             user_id = cursor.lastrowid

#             cursor.execute(social_sql, (user_id, provider, social_id))

#         conn.commit()
#         return user_id
#     except:
#         conn.rollback()
#         raise
#     finally:
#         conn.close()


# =========================
# 소셜 회원가입용 새 함수 추가
# 바로 회원 생성하지 않고, 회원가입 폼을 한 번 더 거쳐서 가입하는 거
# =========================
def create_social_user_with_form(nickname, email, password, provider, social_id, profile_image_url=None):
    provider = provider.upper()
    password_hash = generate_password_hash(password)

    user_sql = """
        INSERT INTO users (email, password_hash, nickname, profile_image_url, role)
        VALUES (%s, %s, %s, %s, 'USER')
    """

    social_sql = """
        INSERT INTO user_social_accounts (user_id, provider, provider_user_id)
        VALUES (%s, %s, %s)
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(user_sql, (email, password_hash, nickname, profile_image_url))
            user_id = cursor.lastrowid

            cursor.execute(social_sql, (user_id, provider, social_id))

        conn.commit()
        return user_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# =========================
# 닉네임으로 이메일 찾기
# =========================
def find_email_by_nickname(nickname):
    sql = """
        SELECT user_id, nickname, email
        FROM users
        WHERE nickname = %s
          AND (status IS NULL OR status <> 'DELETED')
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (nickname,))
            return cursor.fetchone()
    finally:
        conn.close()

# =========================
# 비밀번호 재설정
# 이메일 + 닉네임 일치하는 회원의 비밀번호 변경
# =========================
def reset_user_password(email, nickname, new_password):
    new_password_hash = generate_password_hash(new_password)

    sql = """
        UPDATE users
        SET password_hash = %s
        WHERE email = %s
          AND nickname = %s
          AND (status IS NULL OR status <> 'DELETED')
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (new_password_hash, email, nickname))
            return cursor.rowcount > 0
    finally:
        conn.close()

# =========================
# 일반 회원 탈퇴 처리
# =========================
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

# =========================
# 탈퇴 회원 복구
# =========================
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


# =========================
# 닉네임 변경
# =========================
def update_user_nickname(user_id, new_nickname):
    sql = """
        UPDATE users
        SET nickname = %s
        WHERE user_id = %s
          AND (status IS NULL OR status <> 'DELETED')
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (new_nickname, user_id))
            return cursor.rowcount > 0
    finally:
        conn.close()