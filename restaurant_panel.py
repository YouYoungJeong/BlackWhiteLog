from flask import Blueprint, jsonify
from restaurant_panel_db import get_restaurant_detail, get_restaurant_menus

restaurant_panel_bp = Blueprint('restaurant_panel_bp', __name__)

####
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
####