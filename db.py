# =========================
# 외부 라이브러리 import
# =========================
import os                  # 운영체제 환경변수 접근용
import pymysql             # MariaDB / MySQL 연결용 라이브러리
from dotenv import load_dotenv  # .env 파일 환경변수 로드용

# 비밀번호 해시 생성 / 비밀번호 검사용
from werkzeug.security import generate_password_hash, check_password_hash


# =========================
# .env 파일 로드
# 실행 전에 환경변수(DB 접속정보 등)를 불러옴
# =========================
load_dotenv()


# =========================
# DB 연결 함수
# MariaDB / MySQL 연결 객체를 반환
# 다른 함수들은 이 함수를 통해 DB 접속
# =========================
def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),          # DB 호스트
        port=int(os.getenv("DB_PORT", 3306)),            # DB 포트
        user=os.getenv("DB_USER", "root"),               # DB 사용자명
        password=os.getenv("DB_PASSWORD", ""),           # DB 비밀번호
        database=os.getenv("DB_NAME", "heukbaeklog"),    # 사용할 DB 이름
        charset="utf8mb4",                               # 한글/이모지 깨짐 방지
        cursorclass=pymysql.cursors.DictCursor,          # 결과를 dict 형태로 받음
        autocommit=True,                                 # 자동 커밋
    )


# =========================
# 지역 목록 조회
# 음식점 테이블에서 시/군/구 목록만 중복 없이 가져옴
# 예: 성남시, 수원시, 강남구 ...
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

            # [{"region_sigungu": "성남시"}, {"region_sigungu": "수원시"}]
            # 이런 형태에서 값만 뽑아서 리스트로 반환
            return [row["region_sigungu"] for row in rows]
    finally:
        conn.close()


# =========================
# 카테고리 목록 조회
# 음식점 카테고리 테이블에서 카테고리 id / 이름 조회
# 예: 한식, 중식, 일식 ...
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
# 메인 화면 / 검색 결과 / 카테고리별 목록 등에 사용
#
# 매개변수 설명
# - region      : 지역 필터
# - keyword     : 검색어 필터
# - category_id : 카테고리 필터
# - sort_by     : 정렬 기준
#
# sort_by 종류
# - visits   : 방문수순
# - rating   : 평점순
# - reviews  : 리뷰많은순
# - latest   : 최신등록순
# =========================
def fetch_restaurants(region=None, keyword=None, category_id=None, sort_by="visits"):

    # 정렬 기준별 ORDER BY 문 미리 정의
    order_by_map = {
        "visits": "visit_count DESC, avg_rating DESC, review_count DESC, r.created_at DESC",
        "rating": "avg_rating DESC, review_count DESC, visit_count DESC, r.created_at DESC",
        "reviews": "review_count DESC, avg_rating DESC, visit_count DESC, r.created_at DESC",
        "latest": "r.created_at DESC, visit_count DESC, avg_rating DESC",
    }

    # 잘못된 값이 들어오면 기본값(visits) 사용
    order_by = order_by_map.get(sort_by, order_by_map["visits"])

    # 음식점 기본정보 + 카테고리명 + 방문수 + 리뷰수 + 평점 + 대표이미지 조회
    sql = f"""
        SELECT
            r.restaurant_id,                 -- 음식점 고유 ID
            r.name,                          -- 음식점 이름
            r.address,                       -- 지번 주소
            r.road_address,                  -- 도로명 주소
            r.latitude,                      -- 위도
            r.longitude,                     -- 경도
            r.phone,                         -- 전화번호
            r.business_hours,                -- 영업시간
            r.description,                   -- 설명
            r.region_sido,                   -- 시/도
            r.region_sigungu,                -- 시/군/구
            r.region_dong,                   -- 동/읍/면
            r.status,                        -- 음식점 상태
            r.created_at,                    -- 등록일
            rc.restaurant_category_name AS category_name,  -- 카테고리명

            COALESCE(vs.visit_count, 0) AS visit_count,    -- 방문 수
            COALESCE(rv.review_count, 0) AS review_count,  -- 리뷰 수
            COALESCE(rv.avg_rating, 0) AS avg_rating,      -- 평균 평점

            (
                SELECT COALESCE(ri.thumb_url, ri.image_url)
                FROM restaurant_images ri
                WHERE ri.restaurant_id = r.restaurant_id
                ORDER BY ri.sort_order ASC, ri.image_id ASC
                LIMIT 1
            ) AS image_url                                  -- 대표 이미지 1장

        FROM restaurants r

        -- 음식점 카테고리 이름 가져오기
        LEFT JOIN restaurant_categories rc
            ON r.restaurant_category_id = rc.restaurant_category_id

        -- 음식점별 방문 수 집계
        LEFT JOIN (
            SELECT restaurant_id, COUNT(*) AS visit_count
            FROM visits
            GROUP BY restaurant_id
        ) vs
            ON r.restaurant_id = vs.restaurant_id

        -- 음식점별 리뷰 수 / 평균 평점 집계
        -- reviews 테이블은 visit_id를 통해 restaurants와 연결
        LEFT JOIN (
            SELECT
                v.restaurant_id,
                COUNT(rv.review_id) AS review_count,
                ROUND(AVG(rv.rating), 1) AS avg_rating
            FROM reviews rv
            INNER JOIN visits v
                ON rv.visit_id = v.visit_id
            WHERE rv.status = 'ACTIVE'
            GROUP BY v.restaurant_id
        ) rv
            ON r.restaurant_id = rv.restaurant_id

        WHERE 1=1
    """

    # SQL 파라미터를 담을 리스트
    params = []

    # =========================
    # 운영 가능한 음식점만 조회
    # 상태가 NULL 이거나 OPEN / ACTIVE 인 가게만 보이게 함
    # =========================
    sql += " AND (r.status IS NULL OR r.status IN ('OPEN', 'ACTIVE')) "

    # =========================
    # 지역 필터
    # '전체'가 아니면 해당 지역만 조회
    # =========================
    if region and region != "전체":
        sql += " AND r.region_sigungu = %s "
        params.append(region)

    # =========================
    # 검색어 필터
    # 가게명 / 주소 / 설명 / 카테고리명에서 검색
    # =========================
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

    # =========================
    # 카테고리 필터
    # category_id 값이 있으면 해당 카테고리만 조회
    # =========================
    if category_id and str(category_id).strip():
        sql += " AND r.restaurant_category_id = %s "
        params.append(category_id)

    # =========================
    # 정렬 적용 + 최대 100개 제한
    # =========================
    sql += f" ORDER BY {order_by} LIMIT 100 "

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()

# =========================
# 화면에 바로 쓰기 좋게 후처리
# 이미지 없으면 기본 이미지 넣기
# 숫자값은 None 방지 + 형변환
# =========================
            for row in rows:
                row["image_url"] = row["image_url"] or "https://placehold.co/160x120?text=No+Image"
                row["avg_rating"] = float(row["avg_rating"] or 0)
                row["visit_count"] = int(row["visit_count"] or 0)
                row["review_count"] = int(row["review_count"] or 0)

            return rows
    finally:
        conn.close()