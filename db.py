import os
import pymysql
from dotenv import load_dotenv

# 비밀번호 해시 생성 / 비밀번호 검사용
from werkzeug.security import generate_password_hash, check_password_hash

# .env 파일 로드
load_dotenv()


# =========================
# DB 연결 함수
# =========================
def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "heukbaeklog"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


# =========================
# 지역 목록 조회
# =========================
def fetch_regions():
    sql = """
        SELECT DISTINCT region_sigungu
        FROM restaurants
        WHERE region_sigungu IS NOT NULL
          AND region_sigungu <> ''
        ORDER BY region_sigungu ASC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [row["region_sigungu"] for row in rows]
    finally:
        conn.close()


# =========================
# 카테고리 목록 조회
# =========================
def fetch_categories():
    sql = """
        SELECT restaurant_category_id, restaurant_category_name
        FROM restaurant_categories
        ORDER BY restaurant_category_name ASC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()


# =========================
# 음식점 목록 조회
# =========================
def fetch_restaurants(region=None, keyword=None, category_id=None, sort_by="visits"):
    """
    sort_by:
      - visits   : 방문수순
      - rating   : 평점순
      - reviews  : 리뷰많은순
      - latest   : 최신등록순
    """

    order_by_map = {
        "visits": "visit_count DESC, avg_rating DESC, review_count DESC, r.created_at DESC",
        "rating": "avg_rating DESC, review_count DESC, visit_count DESC, r.created_at DESC",
        "reviews": "review_count DESC, avg_rating DESC, visit_count DESC, r.created_at DESC",
        "latest": "r.created_at DESC, visit_count DESC, avg_rating DESC",
    }

    order_by = order_by_map.get(sort_by, order_by_map["visits"])

    sql = f"""
        SELECT
            r.restaurant_id,
            r.name,
            r.address,
            r.road_address,
            r.latitude,
            r.longitude,
            r.phone,
            r.business_hours,
            r.description,
            r.region_sido,
            r.region_sigungu,
            r.region_dong,
            r.status,
            r.created_at,
            rc.restaurant_category_name AS category_name,

            COALESCE(vs.visit_count, 0) AS visit_count,
            COALESCE(rv.review_count, 0) AS review_count,
            COALESCE(rv.avg_rating, 0) AS avg_rating,

            (
                SELECT COALESCE(ri.thumb_url, ri.image_url)
                FROM restaurant_images ri
                WHERE ri.restaurant_id = r.restaurant_id
                ORDER BY ri.sort_order ASC, ri.image_id ASC
                LIMIT 1
            ) AS image_url

        FROM restaurants r
        LEFT JOIN restaurant_categories rc
            ON r.restaurant_category_id = rc.restaurant_category_id

        LEFT JOIN (
            SELECT restaurant_id, COUNT(*) AS visit_count
            FROM visits
            GROUP BY restaurant_id
        ) vs
            ON r.restaurant_id = vs.restaurant_id

        LEFT JOIN (
            SELECT
                v.restaurant_id,
                COUNT(rv.review_id) AS review_count,
                ROUND(AVG(rv.rating), 1) AS avg_rating
            FROM reviews rv
            INNER JOIN visits v
                ON rv.visit_id = v.visit_id
            GROUP BY v.restaurant_id
        ) rv
            ON r.restaurant_id = rv.restaurant_id

        WHERE 1=1
    """

    params = []

    # 운영 가능한 음식점만 보이게 하는 조건
    # 실제 DB 상태값이 다르면 OPEN / ACTIVE 부분은 맞게 수정하면 됨
    sql += " AND (r.status IS NULL OR r.status IN ('OPEN', 'ACTIVE')) "

    # 지역 필터
    if region and region != "전체":
        sql += " AND r.region_sigungu = %s "
        params.append(region)

    # 검색어 필터
    if keyword:
        sql += """
            AND (
                r.name LIKE %s
                OR r.address LIKE %s
                OR r.road_address LIKE %s
                OR r.description LIKE %s
                OR rc.restaurant_category_name LIKE %s
            )
        """
        like_keyword = f"%{keyword}%"
        params.extend([like_keyword] * 5)

    # 카테고리 필터
    if category_id and str(category_id).strip():
        sql += " AND r.restaurant_category_id = %s "
        params.append(category_id)

    # 정렬 + 최대 100개 제한
    sql += f" ORDER BY {order_by} LIMIT 100 "

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            for row in rows:
                # 이미지가 없으면 기본 이미지 사용
                row["image_url"] = row["image_url"] or "https://placehold.co/160x120?text=No+Image"
                row["avg_rating"] = float(row["avg_rating"] or 0)
                row["visit_count"] = int(row["visit_count"] or 0)
                row["review_count"] = int(row["review_count"] or 0)

            return rows
    finally:
        conn.close()


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

            # 비밀번호 해시 검증
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
        SELECT user_id, email, nickname, status, role
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
# 일반 회원가입
# 현재 users 테이블 기준:
# email / password_hash / nickname 만 저장
# =========================
def create_user(nickname, email, password):
    """
    회원가입 시 비밀번호를 해시로 변환해서 저장
    실제 DB 컬럼명은 password가 아니라 password_hash
    """

    conn = get_connection()

    # 입력받은 비밀번호를 안전하게 해시 처리
    password_hash = generate_password_hash(password)

    sql = """
        INSERT INTO users (email, password_hash, nickname)
        VALUES (%s, %s, %s)
    """

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
        SELECT *
        FROM users
        WHERE provider = %s
          AND social_id = %s
          AND (status IS NULL OR status <> 'DELETED')
        LIMIT 1
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (provider, social_id))
            return cursor.fetchone()
    finally:
        conn.close()


# =========================
# 소셜 회원 생성
# =========================
def create_social_user(nickname, email, provider, social_id, profile_image_url=None):
    sql = """
        INSERT INTO users (nickname, email, password_hash, provider, social_id, profile_image_url)
        VALUES (%s, %s, NULL, %s, %s, %s)
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (nickname, email, provider, social_id, profile_image_url))
        conn.commit()
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

# =========================
# 관리자용 전체 회원 목록 조회
# =========================
def fetch_all_users():
    sql = """
        SELECT user_id, email, nickname, role, status, provider, created_at
        FROM users
        ORDER BY created_at DESC
    """

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()
    finally:
        conn.close()


# =========================
# 관리자용 회원 비활성화
# =========================
def admin_deactivate_user(user_id):
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
# 관리자용 회원 복구
# =========================
def admin_restore_user(user_id):
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
# 관리자 리뷰 관리용 더미 데이터
# 실제 리뷰 테이블 연결 전 임시 사용
# =========================
_dummy_reviews = [
    {
        "review_id": 101,
        "user_nickname": "혜성",
        "restaurant_name": "흑백식당",
        "rating": 4.5,
        "content": "분위기도 좋고 음식도 깔끔해서 재방문 의사 있어요.",
        "status": "ACTIVE",
        "report_count": 0,
        "created_at": "2026-03-13 12:30:00",
    },
    {
        "review_id": 102,
        "user_nickname": "테스트유저",
        "restaurant_name": "서울김밥",
        "rating": 2.0,
        "content": "광고 같은 느낌이 들었고 사진이 실제와 달랐어요.",
        "status": "HIDDEN",
        "report_count": 2,
        "created_at": "2026-03-13 13:10:00",
    },
    {
        "review_id": 103,
        "user_nickname": "민수",
        "restaurant_name": "혜성초밥",
        "rating": 5.0,
        "content": "정말 맛있었습니다. 직원분들도 친절했어요.",
        "status": "ACTIVE",
        "report_count": 1,
        "created_at": "2026-03-13 14:05:00",
    },
    {
        "review_id": 104,
        "user_nickname": "가나다",
        "restaurant_name": "한강분식",
        "rating": 1.5,
        "content": "반복적인 도배성 내용입니다.",
        "status": "DELETED",
        "report_count": 4,
        "created_at": "2026-03-13 15:40:00",
    },
]


# =========================
# 관리자 리뷰 목록 조회
# keyword: 리뷰ID / 작성자 / 음식점명 / 내용 검색
# status: ACTIVE / HIDDEN / DELETED
# =========================
def fetch_admin_reviews(keyword="", status=""):
    keyword = (keyword or "").strip().lower()
    status = (status or "").strip().upper()

    filtered = []

    for review in _dummy_reviews:
        matches_keyword = True
        matches_status = True

        if keyword:
            searchable_text = " ".join([
                str(review["review_id"]),
                review["user_nickname"],
                review["restaurant_name"],
                review["content"],
            ]).lower()
            matches_keyword = keyword in searchable_text

        if status:
            matches_status = review["status"] == status

        if matches_keyword and matches_status:
            filtered.append(review)

    return filtered


# =========================
# 리뷰 단건 조회
# =========================
def get_admin_review_by_id(review_id):
    for review in _dummy_reviews:
        if review["review_id"] == review_id:
            return review
    return None


# =========================
# 리뷰 상태 변경
# ACTIVE / HIDDEN / DELETED
# =========================
def update_admin_review_status(review_id, new_status):
    review = get_admin_review_by_id(review_id)
    if not review:
        return False

    review["status"] = new_status
    return True

# =========================
# 관리자 신고 관리용 더미 데이터
# 실제 신고 테이블 연결 전 임시 사용
# =========================
_dummy_reports = [
    {
        "report_id": 201,
        "review_id": 101,
        "reported_user_nickname": "혜성",
        "report_user_nickname": "민수",
        "restaurant_name": "흑백식당",
        "reason": "욕설/비방",
        "review_content": "분위기도 좋고 음식도 깔끔해서 재방문 의사 있어요.",
        "status": "PENDING",
        "created_at": "2026-03-13 16:10:00",
    },
    {
        "report_id": 202,
        "review_id": 102,
        "reported_user_nickname": "테스트유저",
        "report_user_nickname": "가나다",
        "restaurant_name": "서울김밥",
        "reason": "허위 리뷰",
        "review_content": "광고 같은 느낌이 들었고 사진이 실제와 달랐어요.",
        "status": "RESOLVED",
        "created_at": "2026-03-13 16:35:00",
    },
    {
        "report_id": 203,
        "review_id": 104,
        "reported_user_nickname": "가나다",
        "report_user_nickname": "혜성",
        "restaurant_name": "한강분식",
        "reason": "도배",
        "review_content": "반복적인 도배성 내용입니다.",
        "status": "REJECTED",
        "created_at": "2026-03-13 17:05:00",
    },
]


# =========================
# 관리자 제재 관리용 더미 데이터
# 실제 제재 테이블 연결 전 임시 사용
# =========================
_dummy_sanctions = [
    {
        "sanction_id": 301,
        "user_nickname": "테스트유저",
        "sanction_type": "WARNING",
        "reason": "광고성 리뷰 작성",
        "status": "ACTIVE",
        "created_at": "2026-03-13 17:20:00",
        "expire_at": "-",
    },
    {
        "sanction_id": 302,
        "user_nickname": "가나다",
        "sanction_type": "SUSPEND_3D",
        "reason": "도배성 리뷰 반복 작성",
        "status": "ACTIVE",
        "created_at": "2026-03-13 17:40:00",
        "expire_at": "2026-03-16 17:40:00",
    },
]


# =========================
# 관리자 신고 목록 조회
# keyword: 신고ID / 리뷰ID / 닉네임 / 음식점명 / 사유 검색
# status: PENDING / RESOLVED / REJECTED
# =========================
def fetch_admin_reports(keyword="", status=""):
    keyword = (keyword or "").strip().lower()
    status = (status or "").strip().upper()

    filtered = []

    for report in _dummy_reports:
        matches_keyword = True
        matches_status = True

        if keyword:
            searchable_text = " ".join([
                str(report["report_id"]),
                str(report["review_id"]),
                report["reported_user_nickname"],
                report["report_user_nickname"],
                report["restaurant_name"],
                report["reason"],
                report["review_content"],
            ]).lower()
            matches_keyword = keyword in searchable_text

        if status:
            matches_status = report["status"] == status

        if matches_keyword and matches_status:
            filtered.append(report)

    return filtered


# =========================
# 신고 단건 조회
# =========================
def get_admin_report_by_id(report_id):
    for report in _dummy_reports:
        if report["report_id"] == report_id:
            return report
    return None


# =========================
# 신고 상태 변경
# PENDING / RESOLVED / REJECTED
# =========================
def update_admin_report_status(report_id, new_status):
    report = get_admin_report_by_id(report_id)
    if not report:
        return False

    report["status"] = new_status
    return True


# =========================
# 관리자 제재 목록 조회
# keyword: 제재ID / 닉네임 / 사유 / 제재종류 검색
# status: ACTIVE / RELEASED
# =========================
def fetch_admin_sanctions(keyword="", status=""):
    keyword = (keyword or "").strip().lower()
    status = (status or "").strip().upper()

    filtered = []

    for sanction in _dummy_sanctions:
        matches_keyword = True
        matches_status = True

        if keyword:
            searchable_text = " ".join([
                str(sanction["sanction_id"]),
                sanction["user_nickname"],
                sanction["sanction_type"],
                sanction["reason"],
            ]).lower()
            matches_keyword = keyword in searchable_text

        if status:
            matches_status = sanction["status"] == status

        if matches_keyword and matches_status:
            filtered.append(sanction)

    return filtered


# =========================
# 제재 등록
# sanction_type 예:
# WARNING / SUSPEND_3D / SUSPEND_7D / BAN
# =========================
def create_admin_sanction(user_nickname, sanction_type, reason, expire_at="-"):
    new_id = 301
    if _dummy_sanctions:
        new_id = max(item["sanction_id"] for item in _dummy_sanctions) + 1

    new_item = {
        "sanction_id": new_id,
        "user_nickname": user_nickname,
        "sanction_type": sanction_type,
        "reason": reason,
        "status": "ACTIVE",
        "created_at": "2026-03-13 18:00:00",
        "expire_at": expire_at if expire_at else "-",
    }

    _dummy_sanctions.insert(0, new_item)
    return True


# =========================
# 제재 해제
# =========================
def release_admin_sanction(sanction_id):
    for sanction in _dummy_sanctions:
        if sanction["sanction_id"] == sanction_id:
            sanction["status"] = "RELEASED"
            return True
    return False
# =========================
# 마이페이지 더미 데이터
# 실제 테이블 연결 전 임시 사용
# =========================
_dummy_my_reviews = [
    {
        "review_id": 1,
        "restaurant_name": "흑백식당",
        "rating": 4.5,
        "content": "분위기도 좋고 음식도 깔끔해서 재방문 의사 있어요.",
        "created_at": "2026-03-13 12:30:00",
        "status": "ACTIVE",
    },
    {
        "review_id": 2,
        "restaurant_name": "서울김밥",
        "rating": 3.0,
        "content": "무난했어요. 가볍게 먹기 좋았습니다.",
        "created_at": "2026-03-12 18:10:00",
        "status": "ACTIVE",
    },
]

_dummy_my_favorites = [
    {
        "favorite_id": 1,
        "restaurant_name": "혜성초밥",
        "category": "일식",
        "region": "수원",
        "created_at": "2026-03-13 14:20:00",
    },
    {
        "favorite_id": 2,
        "restaurant_name": "한강분식",
        "category": "분식",
        "region": "서울",
        "created_at": "2026-03-11 10:00:00",
    },
]

_dummy_my_visits = [
    {
        "visit_id": 1,
        "restaurant_name": "흑백식당",
        "visited_at": "2026-03-13 12:00:00",
        "stamp_count": 1,
    },
    {
        "visit_id": 2,
        "restaurant_name": "혜성초밥",
        "visited_at": "2026-03-10 19:20:00",
        "stamp_count": 2,
    },
]

_dummy_my_achievements = [
    {
        "title": "첫 리뷰 작성",
        "description": "리뷰를 1개 이상 작성했어요.",
        "achieved": True,
    },
    {
        "title": "단골 시작",
        "description": "방문 기록 3회를 달성했어요.",
        "achieved": False,
    },
    {
        "title": "맛집 탐험가",
        "description": "서로 다른 음식점 5곳 방문하기.",
        "achieved": False,
    },
]


# =========================
# 내 리뷰 목록 조회
# =========================
def fetch_my_reviews(user_id):
    return _dummy_my_reviews


# =========================
# 내 즐겨찾기 목록 조회
# =========================
def fetch_my_favorites(user_id):
    return _dummy_my_favorites


# =========================
# 내 방문 기록 조회
# =========================
def fetch_my_visits(user_id):
    return _dummy_my_visits


# =========================
# 내 업적 조회
# =========================
def fetch_my_achievements(user_id):
    return _dummy_my_achievements

# =========================
# 닉네임으로 회원 조회
# =========================
def find_user_by_nickname(nickname):
    sql = """
        SELECT user_id, nickname
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

# 비밀번호 해시 생성용
from werkzeug.security import generate_password_hash


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