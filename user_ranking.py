# user_ranking.py
from flask import Blueprint, jsonify
from user_ranking_db import get_all_user_rankings, get_user_dashboard_data, get_user_achievements_data

user_ranking_bp = Blueprint('user_ranking', __name__)

@user_ranking_bp.route('/api/ranking/list')
def api_ranking_list():
    try:
        data = get_all_user_rankings()
        return jsonify(data)
    except Exception as e:
        print(f"❌ Router Error (/api/ranking/list): {e}")
        return jsonify([]), 500

@user_ranking_bp.route('/api/ranking/me')
def api_ranking_me():
    try:
        # 요청하신 대로 우선 user_id 1번 고정
        user_id = 1
        data = get_user_dashboard_data(user_id)
        if data:
            # 유저 뱃지(업적) 데이터 추가 연동
            data['achievements_data'] = get_user_achievements_data(user_id)
            return jsonify(data)
        return jsonify({"message": "User not found"}), 404
    except Exception as e:
        print(f"❌ Router Error (/api/ranking/me): {e}")
        return jsonify({}), 500