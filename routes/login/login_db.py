# =========================
# 공통 DB 연결 함수 import
# =========================
from db import get_connection

# 비밀번호 해시 생성 / 검증용
from werkzeug.security import generate_password_hash


# =========================
# 일반 로그인 검증
# 이메일로 사용자 조회 후 비밀번호가 맞는지 확인
# 탈퇴한 계정은 제외
# =========================
from werkzeug.security import check_password_hash

def verify_user_login(email, password):
    sql = """
        SELECT *
        FROM users
        WHERE email = %s
          AND status <> 'DELETED'
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (email,))
            user = cursor.fetchone()

            if not user:
                return None

            if not check_password_hash(user["password_hash"], password):
                return None

            return user
    finally:
        conn.close()


# =========================
# 이메일로 회원 조회
# 회원가입 중복 확인, 비밀번호 찾기 등에 사용
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
# 닉네임 중복 확인할 때 사용
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
# 비밀번호는 해시로 저장
# 기본 role 은 USER
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
# provider + social_id 기준으로 조회
# user_social_accounts 와 users 테이블 조인
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

    # provider 값은 대문자로 통일
    provider = provider.upper()

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (provider, social_id))
            return cursor.fetchone()
    finally:
        conn.close()


# =========================
# 예전 소셜 회원 생성 함수
# 지금은 사용 안 해서 주석 처리
# 필요하면 나중에 다시 사용할 수 있음
# =========================
# def create_social_user(nickname, email, provider, social_id, profile_image_url=None):
#     provider = provider.upper()
#
#     user_sql = """
#         INSERT INTO users (email, password_hash, nickname, profile_image_url)
#         VALUES (%s, NULL, %s, %s)
#     """
#
#     social_sql = """
#         INSERT INTO user_social_accounts (user_id, provider, provider_user_id)
#         VALUES (%s, %s, %s)
#     """
#
#     conn = get_connection()
#     try:
#         with conn.cursor() as cursor:
#             cursor.execute(user_sql, (email, nickname, profile_image_url))
#             user_id = cursor.lastrowid
#
#             cursor.execute(social_sql, (user_id, provider, social_id))
#
#         conn.commit()
#         return user_id
#     except:
#         conn.rollback()
#         raise
#     finally:
#         conn.close()


# =========================
# 소셜 회원가입
# 소셜 로그인 후 추가 회원정보 입력까지 마치면 저장
# users 테이블 + user_social_accounts 테이블에 함께 저장
# =========================
def create_social_user_with_form(nickname, email, password, provider, social_id, profile_image_url=None):
    provider = provider.upper()
    password_hash = generate_password_hash(password)

    # users 테이블 저장
    user_sql = """
        INSERT INTO users (email, password_hash, nickname, profile_image_url, role)
        VALUES (%s, %s, %s, %s, 'USER')
    """

    # 소셜 계정 연결 테이블 저장
    social_sql = """
        INSERT INTO user_social_accounts (user_id, provider, provider_user_id)
        VALUES (%s, %s, %s)
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # users 테이블에 먼저 저장
            cursor.execute(user_sql, (email, password_hash, nickname, profile_image_url))
            user_id = cursor.lastrowid

            # 방금 생성한 user_id를 user_social_accounts에 저장
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
# 아이디 찾기 기능에서 사용
# 탈퇴한 계정은 제외
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
# 이메일 회원의 비밀번호를 새 비밀번호로 변경
# 탈퇴한 계정은 제외
# =========================
def reset_user_password(email, new_password):
    hashed_password = generate_password_hash(new_password)

    sql = """
        UPDATE users
        SET password_hash = %s
        WHERE email = %s
          AND status <> 'DELETED'
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (hashed_password, email))
            conn.commit()
            return cursor.rowcount > 0
    finally:
        conn.close()


# =========================
# 일반 회원 탈퇴 처리
# 실제 삭제가 아니라 status 값을 DELETED 로 변경
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
# status 값을 ACTIVE 로 다시 변경
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
# 탈퇴하지 않은 회원만 변경 가능
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