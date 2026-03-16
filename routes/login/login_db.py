from db import get_connection
from werkzeug.security import generate_password_hash, check_password_hash


# ==================================================
# 일반 로그인 검증 모듈
# ==================================================
def verify_user_login(email, password):

    # 이메일이 일치하고 삭제되지 않은 사용자 조회
    sql = """
        SELECT *
        FROM users
        WHERE email = %s
        AND (status IS NULL OR status <> 'DELETED')
        LIMIT 1
    """ 

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 이메일로 사용자 조회 사용자 정보 1건 반환
            cursor.execute(sql, (email,))
            user = cursor.fetchone()

            # 사용자가 존재하고 비밀번호 해시가 일치하면 로그인 성공
            if user and check_password_hash(user["password_hash"], password):
                return user
            # 사용자가 없거나 비밀번호가 틀리면 로그인 실패
            return None
    finally:
        # DB 연결 종료
        conn.close()


# ==================================================
# 이메일로 회원 조회
# ==================================================
def find_user_by_email(email):

    # 입력한 이메일과 일치하는 사용자 1명 조회
    sql = """
        SELECT user_id, email, nickname, status
        FROM users
        WHERE email = %s
        LIMIT 1
    """

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 이메일로 사용자 조회하고 사용자 정보 1건 반환
            cursor.execute(sql, (email,))
            return cursor.fetchone()
    finally:
        # DB 연결 종료
        conn.close()


# ==================================================
# 닉네임으로 회원 조회
# ==================================================
def find_user_by_nickname(nickname):

    # 입력한 닉네임과 일치하는 사용자 1명 조회
    sql = """
        SELECT user_id, email, nickname, status
        FROM users
        WHERE nickname = %s
        LIMIT 1
    """

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 닉네임으로 사용자 조회
            cursor.execute(sql, (nickname,))
            return cursor.fetchone()
    finally:
        # DB 연결 종료
        conn.close()


# ==================================================
# 일반 회원가입
# ==================================================
def create_user(nickname, email, password):

    # 입력한 비밀번호를 해시 처리하여 암호화된 값으로 변환
    password_hash = generate_password_hash(password)

    # 이메일, 비밀번호 해시, 닉네임, 권한 정보를 users 테이블에 저장
    sql = """
        INSERT INTO users (email, password_hash, nickname, role)
        VALUES (%s, %s, %s, 'USER')
    """

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 회원 정보 저장 실행
            cursor.execute(sql, (email, password_hash, nickname))
        # INSERT 결과를 DB에 최종 반영
        conn.commit()
    finally:
        # DB 연결 종료
        conn.close()


# ==================================================
# 소셜 로그인용 사용자 조회
# provider + social_id 기준 조회
# ==================================================
def find_user_by_social(provider, social_id):

    # provider와 provider_user_id가 일치하는 사용자 1명 조회
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

    # 소셜 제공자 값을 대문자로 통일
    provider = provider.upper()

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # provider와 social_id로 사용자 조회하고 사용자 정보 1건 반환
            cursor.execute(sql, (provider, social_id))
            return cursor.fetchone()
    finally:
        # DB 연결 종료
        conn.close()


# ==================================================
# 이 유저가 소셜 계정을 이미 연결했는가?
# 예: 내 계정에 지메일 연동을 또 하려고 할 때 중복 연결 방지
# ==================================================
def find_social_account_by_user(user_id, provider):

    # user_id와 provider가 일치하는 소셜 계정 연결 정보 1건 조회
    sql = """
        SELECT social_account_id, user_id, provider, provider_user_id
        FROM user_social_accounts
        WHERE user_id = %s
          AND provider = %s
        LIMIT 1
    """

    # 소셜 제공자 값을 대문자로 통일
    provider = provider.upper()

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # user_id와 provider로 소셜 계정 연결 여부 조회하고 정보 1건 반환
            cursor.execute(sql, (user_id, provider))
            return cursor.fetchone()
    finally:
        # DB 연결 종료
        conn.close()


# ==================================================
# 이 소셜 계정이 이미 다른 유저에게 연결되어 있는가?
# 일반적인 중복 검사
# ==================================================
def is_social_account_already_linked(provider, social_id):

    # provider와 provider_user_id가 일치하는 소셜 계정 연결 정보 1건 조회
    sql = """
        SELECT social_account_id, user_id, provider, provider_user_id
        FROM user_social_accounts
        WHERE provider = %s
        AND provider_user_id = %s
        LIMIT 1
    """

    # 소셜 제공자 값을 대문자로 통일
    provider = provider.upper()

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # provider와 social_id로 소셜 계정 연결 여부 조회하고 정보 1건 반환
            cursor.execute(sql, (provider, social_id))
            return cursor.fetchone()
    finally:
        # DB 연결 종료
        conn.close()


# ==================================================
# 기존 회원 계정에 소셜 계정 연결
# ==================================================
def link_social_account(user_id, provider, social_id):
    
    # 소셜 제공자 값을 대문자로 통일
    provider = provider.upper()

    # 해당 소셜 계정이 이미 다른 계정에 연결되어 있는지 확인
    existing_social = is_social_account_already_linked(provider, social_id)
    if existing_social:
        raise ValueError("이미 다른 계정에 연결된 소셜 계정입니다.")

    # 현재 유저가 같은 provider를 이미 연결했는지 확인
    existing_provider_for_user = find_social_account_by_user(user_id, provider)
    if existing_provider_for_user:
        raise ValueError("이미 해당 소셜 계정이 연결되어 있습니다.")

    # user_id, provider, social_id 정보를 user_social_accounts 테이블에 저장
    sql = """
        INSERT INTO user_social_accounts (user_id, provider, provider_user_id)
        VALUES (%s, %s, %s)
    """

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 소셜 계정 연결 정보 저장 실행
            cursor.execute(sql, (user_id, provider, social_id))
        # INSERT 결과를 DB에 최종 반영
        conn.commit()
    finally:
        # DB 연결 종료
        conn.close()


# ==================================================
# 소셜 회원가입
# 회원가입 폼을 거친 뒤 users + user_social_accounts 저장
# ==================================================
def create_social_user_with_form(nickname, email, password, provider, social_id, profile_image_url=None):
    
    # 소셜 제공자 값을 대문자로 통일
    provider = provider.upper()

    # 입력한 비밀번호를 해시 처리하여 암호화된 값으로 변환
    password_hash = generate_password_hash(password)

    # users 테이블에 기본 회원 정보 저장
    user_sql = """
        INSERT INTO users (email, password_hash, nickname, profile_image_url, role)
        VALUES (%s, %s, %s, %s, 'USER')
    """
    # user_social_accounts 테이블에 소셜 계정 제공 정보 저장
    social_sql = """
        INSERT INTO user_social_accounts (user_id, provider, provider_user_id)
        VALUES (%s, %s, %s)
    """

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # users 테이블에 회원 정보 저장하고 방금 저장된 회원의 user_id 가져오기
            cursor.execute(user_sql, (email, password_hash, nickname, profile_image_url))
            user_id = cursor.lastrowid
            # user_social_accounts 테이블에 소셜 계정 정보 저장
            cursor.execute(social_sql, (user_id, provider, social_id))
        
        # 두 INSERT 결과를 DB에 최종 반영
        conn.commit()
        return user_id
    
    except Exception:
        # 중간에 오류가 발생하면 저장 내용 전체 취소
        conn.rollback()
        raise
    finally:
        # DB 연결 종료
        conn.close()


# ==================================================
# 닉네임으로 이메일 찾기
# ==================================================
def find_email_by_nickname(nickname):

    # 입력한 닉네임과 일치하고 삭제되지 않은 사용자 1명 조회
    sql = """
        SELECT user_id, nickname, email
        FROM users
        WHERE nickname = %s
        AND (status IS NULL OR status <> 'DELETED')
        LIMIT 1
    """

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 닉네임으로 사용자 조회하고 정보 1건 반환
            cursor.execute(sql, (nickname,))
            return cursor.fetchone()
    finally:
        # DB 연결 종료
        conn.close()


# ==================================================
# 비밀번호 재설정
# 이메일 + 닉네임 일치하는 회원의 비밀번호 변경
# ==================================================
def reset_user_password(email, nickname, new_password):

    # 새 비밀번호를 해시 처리하여 암호화된 값으로 변환
    new_password_hash = generate_password_hash(new_password)

    # 이메일과 닉네임이 일치하고 삭제되지 않은 회원의 비밀번호 수정
    sql = """
        UPDATE users
        SET password_hash = %s
        WHERE email = %s
        AND nickname = %s
        AND (status IS NULL OR status <> 'DELETED')
    """

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 새 비밀번호 해시로 비밀번호 변경 실행
            cursor.execute(sql, (new_password_hash, email, nickname))
            
            # # 변경된 행이 있는지 확인 및 DB 저장
            changed = cursor.rowcount > 0
        conn.commit()

        # 비밀번호 변경 성공 여부 반환
        return changed
    finally:
        # DB 연결 종료
        conn.close()


# ==================================================
# 일반 회원 탈퇴 처리
# ==================================================
def withdraw_user(user_id):

    # 해당 user_id의 회원 상태를 DELETED로 변경
    sql = """
        UPDATE users
        SET status = 'DELETED'
        WHERE user_id = %s
    """

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 회원 상태를 탈퇴 상태로 변경하고 DB 저장
            cursor.execute(sql, (user_id,))
        conn.commit()
    finally:
        # DB 연결 종료
        conn.close()


# ==================================================
# 탈퇴 회원 복구
# ==================================================
def restore_user(user_id):

    # 해당 user_id의 회원 상태를 ACTIVE로 변경
    sql = """
        UPDATE users
        SET status = 'ACTIVE'
        WHERE user_id = %s
    """

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 회원 상태를 활성 상태로 복구하고 DB 저장
            cursor.execute(sql, (user_id,))
        conn.commit()
    finally:
        # DB 연결 종료
        conn.close()


# ==================================================
# 닉네임 변경
# ==================================================
def update_user_nickname(user_id, new_nickname):

    # 해당 user_id의 닉네임을 새 닉네임으로 변경
    # 단, 탈퇴한 회원은 변경 대상에서 제외
    sql = """
        UPDATE users
        SET nickname = %s
        WHERE user_id = %s
          AND (status IS NULL OR status <> 'DELETED')
    """

    # DB 연결
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 새 닉네임으로 회원 정보 수정
            cursor.execute(sql, (new_nickname, user_id))
            # 변경된 행이 있는지 확인 및 DB 저장
            changed = cursor.rowcount > 0
        conn.commit()

        # 닉네임 변경 성공 여부 반환
        return changed
    finally:
        # DB 연결 종료
        conn.close()