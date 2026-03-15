import os
import uuid
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

    # 세션에서 현재 로그인한 유저 ID 가져오기
    current_user_id = session.get('user_id')

    # 각 리뷰에 '내 리뷰인지' 판별하는 is_mine 플래그 추가
    for review in reviews:
        review['is_mine'] = (current_user_id == review['user_id'])

    return jsonify(reviews)

@restaurant_panel_bp.route("/api/restaurants/<int:restaurant_id>/reviews", methods=["POST"])
def api_add_review(restaurant_id):
    try:
        # 데이터 수신 및 타입 변환
        rating = request.form.get("rating")
        content = request.form.get("content")
        images = request.files.getlist("images") # 프론트에서 보낸 파일들 받기

        if not rating or not content:
            return jsonify({"success": False, "message": "데이터가 부족합니다."}), 400

        # 유저 ID 설정 (반드시 DB에 존재하는 ID여야 함)
        user_id = session.get('user_id', 1) 

        # 로컬 폴더에 이미지 저장 로직
        image_urls = []
        if images and images[0].filename != '':
            # 폴더 경로 설정 및 없으면 생성
            upload_dir = os.path.join("static", "img", "review_img")
            os.makedirs(upload_dir, exist_ok=True)
            
            for img in images:
                if img and img.filename:
                    # 파일명 중복 방지를 위해 UUID 사용 (확장자 유지)
                    ext = img.filename.rsplit('.', 1)[-1].lower() if '.' in img.filename else 'jpg'
                    unique_filename = f"{uuid.uuid4().hex}.{ext}"
                    filepath = os.path.join(upload_dir, unique_filename)
                    
                    # 파일 실제 저장
                    img.save(filepath)
                    
                    # DB에 저장할 웹 접근 경로 생성 (윈도우의 \를 /로 변경)
                    web_path = f"/{filepath.replace(os.sep, '/')}"
                    image_urls.append(web_path)
                    
        # DB 함수 호출 
        success = save_restaurant_review(restaurant_id, user_id, int(rating), content, image_urls)
        
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
    user_id = session.get('user_id') # 유저 아이디 받아 삭제 기능

    if not user_id:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401
    
    from restaurant_panel_db import delete_review_transaction
    if delete_review_transaction(review_id, user_id):
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "삭제 권한이 없거나 오류가 발생했습니다."}), 403