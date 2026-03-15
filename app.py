# =========================
# Flask 기본 기능들 import
# =========================
from flask import Flask, jsonify, render_template, request, session

# .env 파일에 저장한 환경변수 불러오기
from dotenv import load_dotenv

# 운영체제 환경변수 접근용
import os

# =========================
# 메일 객체 import
# routes/login/extensions.py 에 있는 mail 가져오기
# =========================
from routes.login.extensions import mail

# =========================
# 블루프린트 / 라우트 import
# =========================
from routes.owner.owner_routes import register_owner_routes
from routes.admin.admin_routes import admin_bp
from routes.login.login_routes import login_bp
from routes.mypage.mypage_routes import mypage_bp
from routes.restaurant.restaurant_panel import restaurant_panel_bp
from routes.ranking.user_ranking import user_ranking_bp

# =========================
# DB 함수 import
# =========================
from db import fetch_categories, fetch_regions, fetch_restaurants

# =========================
# .env 로드
# =========================
load_dotenv()

# =========================
# Flask 앱 생성
# =========================
app = Flask(__name__)

# Flask 시크릿 키 설정
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

# =========================
# 메일 서버 설정
# .env 파일의 값을 읽어와서 Gmail SMTP 연결
# =========================
app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER")

# Gmail은 TLS 사용
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False

# Flask-Mail 앱 연결
mail.init_app(app)

# =========================
# 블루프린트 등록
# =========================
app.register_blueprint(admin_bp)
app.register_blueprint(login_bp)
app.register_blueprint(mypage_bp)
app.register_blueprint(restaurant_panel_bp)
app.register_blueprint(user_ranking_bp)

# 일반 함수형 라우트 등록
register_owner_routes(app)

# =========================
# 메인 페이지
# =========================
@app.route("/")
def index():
    # 지역 / 카테고리 목록 조회
    regions = ["전체"] + fetch_regions()
    categories = fetch_categories()

    # 로그인 세션 정보 가져오기
    user_email = session.get("user_email")
    user_nickname = session.get("user_nickname")

    # 메인 페이지 렌더링
    return render_template(
        "index.html",
        regions=regions,
        categories=categories,
        user_email=user_email,
        user_nickname=user_nickname
    )

# =========================
# 음식점 API
# =========================
@app.route("/api/restaurants")
def api_restaurants():
    # 쿼리스트링 값 받기
    region = request.args.get("region", default="전체", type=str)
    keyword = request.args.get("keyword", default="", type=str).strip()
    category_id = request.args.get("category_id", default="", type=str).strip()
    sort_by = request.args.get("sort_by", default="visits", type=str)

    # DB에서 음식점 목록 조회
    items = fetch_restaurants(
        region=region,
        keyword=keyword,
        category_id=category_id if category_id else None,
        sort_by=sort_by,
    )

    # JSON 응답 반환
    return jsonify(items)

# =========================
# 사장님 회원가입 페이지
# =========================
@app.route("/seller/register")
def seller_register():
    return render_template("owner/owner_register.html")

# =========================
# 서버 실행
# =========================
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)