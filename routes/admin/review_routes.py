# =========================
# Flask 기본 기능 import
# =========================
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify

# =========================
# DB 함수 import
# =========================
from db import delete_review

# =========================
# 관리자 블루프린트
# 이미 있다면 이 줄은 기존 것 유지
# =========================
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# =========================
# 관리자 리뷰 삭제
# review_id에 해당하는 리뷰를 삭제
# 실제 주소: /admin/reviews/<review_id>/delete
# =========================
@admin_bp.route("/reviews/<int:review_id>/delete", methods=["POST"])
def admin_delete_review(review_id):
    success = delete_review(review_id)

    if not success:
        return jsonify({
            "success": False,
            "message": "리뷰를 찾을 수 없습니다."
        }), 404

    return jsonify({
        "success": True,
        "message": "리뷰가 삭제되었습니다."
    })