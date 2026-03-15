# user_ranking.py
from flask import Blueprint, jsonify, session
from .user_ranking_db import get_all_user_rankings, get_user_dashboard_data, get_user_achievements_data, get_ranking_summary, check_and_update_tier

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
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"message": "로그인이 필요합니다."}),401
        # 티어 확인
        check_and_update_tier(user_id)
        data = get_user_dashboard_data(user_id)
        if data:
            # 유저 뱃지(업적) 데이터 추가 연동
            data['achievements_data'] = get_user_achievements_data(user_id)

            # 스캐너 함수를 불러와서 미션 데이터를 추가
            from routes.ranking.user_ranking_db import get_user_missions_status
            data['missions_data'] = get_user_missions_status(user_id)
            
            return jsonify(data)
        return jsonify({"message": "User not found"}), 404
    except Exception as e:
        print(f"❌ Router Error (/api/ranking/me): {e}")
        return jsonify({}), 500

# 랭킹 요약 
@user_ranking_bp.route('/api/ranking/summary')
def api_ranking_summary():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401
        # 티어 확인 
        check_and_update_tier(user_id)    
        data = get_ranking_summary(user_id)
        if data:
            return jsonify(data)
        return jsonify({"error": "Data not found"}), 404
    except Exception as e:
        print(f"❌ Router Error (/api/ranking/summary): {e}")
        return jsonify({}), 500