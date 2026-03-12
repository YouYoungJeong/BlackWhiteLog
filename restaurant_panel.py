from flask import Blueprint, jsonify, request, session
from restaurant_panel_db import get_restaurant_detail, get_restaurant_menus, get_restaurant_reviews, save_restaurant_review

restaurant_panel_bp = Blueprint('restaurant_panel_bp', __name__)

@restaurant_panel_bp.route("/api/restaurants/<int:restaurant_id>")
def api_restaurant_detail(restaurant_id):
    """특정 음식점 상세 정보 반환 API"""
    detail = get_restaurant_detail(restaurant_id)
    if detail:
        return jsonify(detail)
    return jsonify({"error": "Restaurant not found"}), 404

@restaurant_panel_bp.route("/api/restaurants/<int:restaurant_id>/menus")
def api_restaurant_menus(restaurant_id):
    """특정 음식점의 메뉴 목록 반환 API"""
    menus = get_restaurant_menus(restaurant_id)
    return jsonify(menus)

@restaurant_panel_bp.route("/api/restaurants/<int:restaurant_id>/reviews")
def api_restaurant_reviews(restaurant_id):
    """특정 음식점의 리뷰 목록 반환 API"""
    reviews = get_restaurant_reviews(restaurant_id)
    return jsonify(reviews)

@restaurant_panel_bp.route("/api/restaurants/<int:restaurant_id>/reviews", methods=["POST"])
def api_add_review(restaurant_id):
    try:
        # 1. 데이터 수신 및 타입 변환
        rating = request.form.get("rating")
        content = request.form.get("content")
        
        # [디버깅] 데이터가 잘 왔는지 서버 터미널에서 확인
        print(f">>> [리뷰등록 요청] 식당ID: {restaurant_id}, 별점: {rating}, 내용: {content}")

        if not rating or not content:
            return jsonify({"success": False, "message": "데이터가 부족합니다."}), 400

        # 2. 유저 ID 설정 (반드시 DB에 존재하는 ID여야 함)
        user_id = session.get('user_id', 1) 

        # 3. DB 함수 호출 (4개의 인자 확인)
        from restaurant_panel_db import save_restaurant_review
        success = save_restaurant_review(restaurant_id, user_id, int(rating), content)
        
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "DB 저장 실패 (함수 반환값 False)"})

    except Exception as e:
        # 여기가 핵심: 에러 내용을 터미널에 자세히 출력합니다.
        print(f"서버 에러 발생: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500
    

@restaurant_panel_bp.route("/api/reviews/<int:review_id>", methods=["DELETE"])
def api_delete_review(review_id):
    user_id = session.get('user_id', 1) # 로그인 구현 전까지 임시 1
    
    from restaurant_panel_db import delete_review_transaction
    if delete_review_transaction(review_id, user_id):
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "삭제 권한이 없거나 오류가 발생했습니다."}), 403