# Flask 기본 기능들 import
from flask import Flask, jsonify, render_template, request, session, url_for
# .env 파일에 저장한 환경변수 불러오기
from dotenv import load_dotenv
# 운영체제 환경변수 접근용
import os

from routes.owner.owner_routes import register_owner_routes
from routes.admin.admin_routes import admin_bp
from routes.login.login_routes import login_bp
from routes.mypage.mypage_routes import mypage_bp
from routes.restaurant.restaurant_panel import restaurant_panel_bp
from routes.ranking.user_ranking import user_ranking_bp

from db import (
    fetch_categories,
    fetch_regions,
    fetch_restaurants,
    fetch_favorite_restaurants,
    toggle_favorite_restaurant,
)

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

app.register_blueprint(admin_bp)
app.register_blueprint(login_bp)
app.register_blueprint(mypage_bp)
app.register_blueprint(restaurant_panel_bp)
app.register_blueprint(user_ranking_bp)
register_owner_routes(app)


# =========================
# 메인 페이지
# =========================
@app.route("/")
def index():
    regions = ["전체"] + fetch_regions()
    categories = fetch_categories()
    user_email = session.get("user_email")
    user_nickname = session.get("user_nickname")
    user_id = session.get("user_id")

    return render_template(
        "index.html",
        regions=regions,
        categories=categories,
        user_email=user_email,
        user_nickname=user_nickname,
        user_id=user_id
    )


# =========================
# 음식점 API
# =========================
@app.route("/api/restaurants")
def api_restaurants():
    region = request.args.get("region", default="전체", type=str)
    keyword = request.args.get("keyword", default="", type=str).strip()
    category_id = request.args.get("category_id", default="", type=str).strip()
    sort_by = request.args.get("sort_by", default="visits", type=str)
    user_id = session.get("user_id")

    items = fetch_restaurants(
        region=region,
        keyword=keyword,
        category_id=category_id if category_id else None,
        user_id=user_id,
        sort_by=sort_by,
    )

    return jsonify(items)

# =========================
# 즐겨찾기 API
# =========================
@app.route("/api/favorites")
def api_favorites():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "message": "로그인 후 이용해 주세요.",
            "login_url": url_for("login.login")
        }), 401

    region = request.args.get("region", default="전체", type=str)
    category_id = request.args.get("category_id", default="", type=str).strip()

    items = fetch_favorite_restaurants(
        user_id=user_id,
        region=region,
        category_id=category_id if category_id else None,
    )

    return jsonify(items)

@app.route("/api/favorites/<int:restaurant_id>/toggle", methods=["POST"])
def api_toggle_favorite(restaurant_id):
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({
            "message": "로그인 후 이용해 주세요.",
            "login_url": url_for("login.login")
        }), 401

    is_favorite = toggle_favorite_restaurant(user_id, restaurant_id)

    return jsonify({
        "restaurant_id": restaurant_id,
        "is_favorite": is_favorite
    })

@app.route("/seller/register")
def seller_register():
    return render_template("owner/owner_register.html")


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "True") == "True")
