# Flask 기능 import
from flask import Blueprint, render_template, request, redirect, url_for, flash, session

# 데코레이터 함수 감싸기용
from functools import wraps

# 음식점 관리용 더미 데이터 import
from admin_dummy_data import (
    DUMMY_CATEGORIES,
    DUMMY_RESTAURANTS,
    get_category_name,
    get_restaurant_by_id,
    get_next_restaurant_id,
)

# 관리자 블루프린트 생성
# url_for 쓸 때 admin.붙음
admin_bp = Blueprint("admin", __name__)


# =========================
# 관리자 권한 체크 데코레이터
# =========================
def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        # 로그인 안 했으면 로그인 페이지로 이동
        if "user_id" not in session:
            flash("로그인이 필요합니다.")
            return redirect(url_for("login"))

        # 관리자만 접근 가능
        if session.get("role") != "ADMIN":
            flash("관리자만 접근할 수 있습니다.")
            return redirect(url_for("index"))

        return view_func(*args, **kwargs)
    return wrapper


# =========================
# 관리자 음식점 목록
# =========================
@admin_bp.route("/admin/restaurants")
@admin_required
def admin_restaurants():
    # 검색어 받기
    keyword = request.args.get("keyword", "").strip()

    # 기본은 전체 목록
    filtered_restaurants = DUMMY_RESTAURANTS

    # 검색어가 있으면 이름 기준 검색
    if keyword:
        filtered_restaurants = [
            r for r in DUMMY_RESTAURANTS
            if keyword.lower() in r["restaurant_name"].lower()
        ]

    # 카테고리명 붙여서 템플릿에 전달
    restaurants_with_category = []
    for r in filtered_restaurants:
        item = r.copy()
        item["restaurant_category_name"] = get_category_name(r["restaurant_category_id"])
        restaurants_with_category.append(item)

    return render_template(
        "admin/admin_restaurants.html",
        restaurants=restaurants_with_category,
        keyword=keyword,
    )


# =========================
# 관리자 음식점 등록
# =========================
@admin_bp.route("/admin/restaurants/create", methods=["GET", "POST"])
@admin_required
def admin_restaurant_create():
    # GET 요청이면 등록 폼 보여주기
    if request.method == "GET":
        return render_template(
            "admin/admin_restaurant_form.html",
            mode="create",
            categories=DUMMY_CATEGORIES,
            restaurant=None,
        )

    # POST 요청이면 폼 데이터 받기
    restaurant_name = request.form.get("restaurant_name", "").strip()
    restaurant_category_id = request.form.get("restaurant_category_id", "").strip()
    region_sigungu = request.form.get("region_sigungu", "").strip()
    address = request.form.get("address", "").strip()
    phone = request.form.get("phone", "").strip()

    # 이름은 필수 입력
    if not restaurant_name:
        flash("음식점 이름을 입력해주세요.")
        return render_template(
            "admin/admin_restaurant_form.html",
            mode="create",
            categories=DUMMY_CATEGORIES,
            restaurant=None,
        )

    # 새 음식점 더미 데이터 생성
    new_restaurant = {
        "restaurant_id": get_next_restaurant_id(),
        "restaurant_name": restaurant_name,
        "restaurant_category_id": int(restaurant_category_id) if restaurant_category_id else 1,
        "region_sigungu": region_sigungu,
        "address": address,
        "phone": phone,
    }

    # 더미 목록에 추가
    DUMMY_RESTAURANTS.append(new_restaurant)

    flash("음식점이 등록되었습니다.")
    return redirect(url_for("admin.admin_restaurants"))


# =========================
# 관리자 음식점 수정
# =========================
@admin_bp.route("/admin/restaurants/<int:restaurant_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_restaurant_edit(restaurant_id):
    # 수정할 음식점 찾기
    restaurant = get_restaurant_by_id(restaurant_id)

    # 없는 음식점이면 목록으로 이동
    if not restaurant:
        flash("해당 음식점을 찾을 수 없습니다.")
        return redirect(url_for("admin.admin_restaurants"))

    # GET 요청이면 수정 폼 보여주기
    if request.method == "GET":
        return render_template(
            "admin/admin_restaurant_form.html",
            mode="edit",
            categories=DUMMY_CATEGORIES,
            restaurant=restaurant,
        )

    # POST 요청이면 수정값 받기
    restaurant_name = request.form.get("restaurant_name", "").strip()
    restaurant_category_id = request.form.get("restaurant_category_id", "").strip()
    region_sigungu = request.form.get("region_sigungu", "").strip()
    address = request.form.get("address", "").strip()
    phone = request.form.get("phone", "").strip()

    # 이름은 필수 입력
    if not restaurant_name:
        flash("음식점 이름을 입력해주세요.")
        return render_template(
            "admin/admin_restaurant_form.html",
            mode="edit",
            categories=DUMMY_CATEGORIES,
            restaurant=restaurant,
        )

    # 더미 데이터 수정
    restaurant["restaurant_name"] = restaurant_name
    restaurant["restaurant_category_id"] = int(restaurant_category_id) if restaurant_category_id else 1
    restaurant["region_sigungu"] = region_sigungu
    restaurant["address"] = address
    restaurant["phone"] = phone

    flash("음식점 정보가 수정되었습니다.")
    return redirect(url_for("admin.admin_restaurants"))


# =========================
# 관리자 음식점 삭제
# =========================
@admin_bp.route("/admin/restaurants/<int:restaurant_id>/delete", methods=["POST"])
@admin_required
def admin_restaurant_delete(restaurant_id):
    # 삭제할 음식점 찾기
    target = get_restaurant_by_id(restaurant_id)

    # 없으면 에러 메시지
    if not target:
        flash("삭제할 음식점을 찾지 못했습니다.")
        return redirect(url_for("admin.admin_restaurants"))

    # 더미 목록에서 제거
    DUMMY_RESTAURANTS.remove(target)

    flash("음식점이 삭제되었습니다.")
    return redirect(url_for("admin.admin_restaurants"))