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