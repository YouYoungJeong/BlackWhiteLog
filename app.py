# Flask 기본 기능들 import
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session

# .env 파일에 저장한 환경변수 불러오기
from dotenv import load_dotenv

# 데코레이터 함수 감싸기용
from functools import wraps

# 운영체제 환경변수 접근용
import os

# 외부 API 요청용
import requests

# owner-routes.py import
from owner_routes import register_owner_routes


# OAuth state 값 생성용 (보안)
import secrets

# 관리자 음식점 관리 블루프린트
from admin_routes import admin_bp

# db.py 에서 필요한 함수들 import
from db import (
    fetch_categories,
    fetch_regions,
    fetch_restaurants,
    verify_user_login,
    create_user,
    find_user_by_email,
    find_user_by_social,
    create_social_user,
    withdraw_user,
    restore_user,
    fetch_all_users,
    admin_deactivate_user,
    admin_restore_user,
    fetch_admin_reviews,
    update_admin_review_status,
    fetch_admin_reports,
    update_admin_report_status,
    fetch_admin_sanctions,
    create_admin_sanction,
    release_admin_sanction,
    fetch_my_reviews,
    fetch_my_favorites,
    fetch_my_visits,
    fetch_my_achievements,
    update_user_nickname,
    find_user_by_nickname,
    find_email_by_nickname,   # 닉네임으로 이메일 찾기
    reset_user_password,      # 비밀번호 재설정
)

# .env 파일 로드
load_dotenv()

# Flask 앱 생성
app = Flask(__name__)

#### 레스토랑 판넬 블루프린트(모듈화)  
from restaurant_panel import restaurant_panel_bp  # 분리한 파일 임포트
app.register_blueprint(restaurant_panel_bp) # 앱에 등록
#### 레스토랑 판넬 블루프린트(모듈화)
#### 랭크 블루프린트
from user_ranking import user_ranking_bp
app.register_blueprint(user_ranking_bp)
#### 랭크 블루프린트

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

# 관리자 음식점 관리 블루프린트 등록
app.register_blueprint(admin_bp)


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

        # role 이 ADMIN 이 아니면 접근 차단
        if session.get("role") != "ADMIN":
            flash("관리자만 접근할 수 있습니다.")
            return redirect(url_for("index"))

        return view_func(*args, **kwargs)
    return wrapper


# =========================
# 로그인 필수 데코레이터
# =========================
def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("로그인이 필요합니다.")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


# =========================
# 메인 페이지
# =========================
@app.route("/")
def index():
    # 지역 목록 맨 앞에 "전체" 추가
    regions = ["전체"] + fetch_regions()

    # 카테고리 목록 조회
    categories = fetch_categories()

    # 로그인된 사용자 정보 세션에서 가져오기
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
    # URL 쿼리스트링 값 받기
    region = request.args.get("region", default="전체", type=str)
    keyword = request.args.get("keyword", default="", type=str).strip()
    category_id = request.args.get("category_id", default="", type=str).strip()
    sort_by = request.args.get("sort_by", default="visits", type=str)

    # DB에서 조건에 맞는 음식점 조회
    items = fetch_restaurants(
        region=region,
        keyword=keyword,
        category_id=category_id if category_id else None,
        sort_by=sort_by,
    )

    # JSON 형태로 반환
    return jsonify(items)

# 이종민 추가 3월 12일 3번째
@app.route("/seller/register")
def seller_register():
    return render_template("seller_register.html")



# ===== Owner routes =====
register_owner_routes(app)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")



# =========================
# 일반 로그인
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = verify_user_login(email, password)

        if user:
            session["user_email"] = user["email"]
            session["user_nickname"] = user["nickname"]
            session["user_id"] = user["user_id"]
            session["role"] = user.get("role", "USER")
            session["login_provider"] = "local"
            return redirect(url_for("index"))

        flash("이메일 또는 비밀번호가 올바르지 않거나 탈퇴한 계정입니다.")
        return redirect(url_for("login"))

    return render_template("login.html")


# =========================
# 일반 회원가입
# =========================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        password_confirm = request.form.get("password_confirm", "").strip()

        email_checked = request.form.get("email_checked", "false")
        checked_email_value = request.form.get("checked_email_value", "").strip()

        nickname_checked = request.form.get("nickname_checked", "false")
        checked_nickname_value = request.form.get("checked_nickname_value", "").strip()

        # 필수값 검사
        if not nickname or not email or not password or not password_confirm:
            flash("모든 값을 입력해주세요.")
            return redirect(url_for("signup"))

        # 비밀번호 확인 일치 여부
        if password != password_confirm:
            flash("비밀번호와 비밀번호 확인이 일치하지 않습니다.")
            return redirect(url_for("signup"))

        # 이메일 중복확인 여부 검사
        if email_checked != "true" or checked_email_value != email:
            flash("이메일 중복 확인을 해주세요.")
            return redirect(url_for("signup"))

        # 닉네임 중복확인 여부 검사
        if nickname_checked != "true" or checked_nickname_value != nickname:
            flash("닉네임 중복 확인을 해주세요.")
            return redirect(url_for("signup"))

        # 서버에서 한 번 더 이메일 중복 검사
        # 프론트만 믿으면 안 되므로 DB에서 다시 확인
        existing_user = find_user_by_email(email)
        if existing_user:
            flash("이미 가입된 이메일입니다.")
            return redirect(url_for("signup"))

        # 서버에서 닉네임 중복 검사
        existing_nickname = find_user_by_nickname(nickname)
        if existing_nickname:
            flash("이미 사용 중인 닉네임입니다.")
            return redirect(url_for("signup"))

        # 회원 생성
        create_user(nickname, email, password)

        flash("회원가입이 완료되었습니다. 로그인해주세요.")
        return redirect(url_for("login"))

    return render_template("signup.html")

# =========================
# 회원가입 시 이메일 중복 확인
# =========================
@app.route("/api/check-duplicate")
def check_duplicate():
    # 프론트에서 type=email, value=입력값 형태로 보냄
    check_type = request.args.get("type", "").strip()
    value = request.args.get("value", "").strip()

    # 값이 비어 있으면 바로 에러 응답
    if not value:
        return jsonify({
            "available": False,
            "message": "값을 입력해주세요."
        })

    # 이메일 중복 확인
    if check_type == "email":
        user = find_user_by_email(value)

        if user:
            return jsonify({
                "available": False,
                "message": "이미 사용 중인 이메일입니다."
            })
        else:
            return jsonify({
                "available": True,
                "message": "사용 가능한 이메일입니다."
            })

    # 필요하면 닉네임 중복 확인도 여기에 추가 가능
    elif check_type == "nickname":
        user = find_user_by_nickname(value)

        if user:
            return jsonify({
                "available": False,
                "message": "이미 사용 중인 닉네임입니다."
            })
        else:
            return jsonify({
                "available": True,
                "message": "사용 가능한 닉네임입니다."
            })

    # 지원하지 않는 타입일 때
    return jsonify({
        "available": False,
        "message": "잘못된 요청입니다."
    })

# =========================
# 이메일 찾기
# 닉네임으로 가입 이메일 조회
# =========================
@app.route("/find-id", methods=["GET", "POST"])
def find_id():
    found_email = None

    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()

        if not nickname:
            flash("닉네임을 입력해주세요.")
            return redirect(url_for("find_id"))

        user = find_email_by_nickname(nickname)

        if not user:
            flash("일치하는 회원 정보를 찾을 수 없습니다.")
            return redirect(url_for("find_id"))

        found_email = user["email"]

    return render_template("find_id.html", found_email=found_email)


# =========================
# 비밀번호 찾기 / 재설정
# 이메일 + 닉네임 확인 후 새 비밀번호로 변경
# =========================
@app.route("/find-password", methods=["GET", "POST"])
def find_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        nickname = request.form.get("nickname", "").strip()
        new_password = request.form.get("new_password", "").strip()
        new_password_confirm = request.form.get("new_password_confirm", "").strip()

        if not email or not nickname or not new_password or not new_password_confirm:
            flash("모든 항목을 입력해주세요.")
            return redirect(url_for("find_password"))

        if new_password != new_password_confirm:
            flash("새 비밀번호가 일치하지 않습니다.")
            return redirect(url_for("find_password"))

        if len(new_password) < 4:
            flash("비밀번호는 4자 이상 입력해주세요.")
            return redirect(url_for("find_password"))

        success = reset_user_password(email, nickname, new_password)

        if not success:
            flash("입력한 정보와 일치하는 회원을 찾을 수 없습니다.")
            return redirect(url_for("find_password"))

        flash("비밀번호가 재설정되었습니다. 다시 로그인해주세요.")
        return redirect(url_for("login"))

    return render_template("find_password.html")

# =========================
# 로그아웃
# =========================
@app.route("/logout")
def logout():
    provider = session.get("login_provider")
    session.clear()

    if provider == "kakao":
        kakao_rest_api_key = os.getenv("KAKAO_REST_API_KEY")
        kakao_logout_redirect_uri = os.getenv("KAKAO_LOGOUT_REDIRECT_URI")

        logout_url = (
            "https://kauth.kakao.com/oauth/logout"
            f"?client_id={kakao_rest_api_key}"
            f"&logout_redirect_uri={kakao_logout_redirect_uri}"
        )
        return redirect(logout_url)

    if provider in ["naver", "google", "local", None]:
        flash("로그아웃되었습니다.")
        return redirect(url_for("index"))


# =========================
# 카카오 로그아웃 콜백
# =========================
@app.route("/logout/kakao/callback")
def logout_kakao_callback():
    flash("로그아웃되었습니다.")
    return redirect(url_for("index"))


# =========================
# 카카오 로그인 요청
# =========================
@app.route("/login/kakao")
def login_kakao():
    kakao_rest_api_key = os.getenv("KAKAO_REST_API_KEY")
    redirect_uri = os.getenv("KAKAO_REDIRECT_URI")

    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    auth_url = (
        "https://kauth.kakao.com/oauth/authorize"
        f"?client_id={kakao_rest_api_key}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&state={state}"
    )
    return redirect(auth_url)


# =========================
# 카카오 로그인 콜백
# =========================
@app.route("/login/kakao/callback")
def login_kakao_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        flash("카카오 로그인에 실패했습니다.")
        return redirect(url_for("login"))

    if state != session.get("oauth_state"):
        flash("잘못된 요청입니다.")
        return redirect(url_for("login"))

    token_data = {
        "grant_type": "authorization_code",
        "client_id": os.getenv("KAKAO_REST_API_KEY"),
        "redirect_uri": os.getenv("KAKAO_REDIRECT_URI"),
        "code": code,
    }

    client_secret = os.getenv("KAKAO_CLIENT_SECRET")
    if client_secret:
        token_data["client_secret"] = client_secret

    token_res = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data=token_data,
        headers={"Content-type": "application/x-www-form-urlencoded;charset=utf-8"},
    )

    token_json = token_res.json()
    access_token = token_json.get("access_token")

    if not access_token:
        flash(f"카카오 토큰 발급 실패: {token_json}")
        return redirect(url_for("login"))

    user_res = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-type": "application/x-www-form-urlencoded;charset=utf-8",
        },
    )

    user_json = user_res.json()

    social_id = str(user_json["id"])
    kakao_account = user_json.get("kakao_account", {})
    profile = kakao_account.get("profile", {})

    email = kakao_account.get("email")
    if not email:
        email = f"kakao_{social_id}@kakao.local"

    nickname = profile.get("nickname") or f"kakao_{social_id}"
    profile_image_url = profile.get("profile_image_url")

    user = find_user_by_social("kakao", social_id)

    if user:
        session["user_email"] = user["email"]
        session["user_nickname"] = user["nickname"]
        session["user_id"] = user["user_id"]
        session["role"] = user.get("role", "USER")
        session["login_provider"] = "kakao"
        flash("카카오 로그인 성공")
        return redirect(url_for("index"))

    existing_user = find_user_by_email(email)

    if existing_user:
        if existing_user.get("status") == "DELETED":
            restore_user(existing_user["user_id"])
            user = find_user_by_email(email)

            session["user_email"] = user["email"]
            session["user_nickname"] = user["nickname"]
            session["user_id"] = user["user_id"]
            session["role"] = user.get("role", "USER")
            session["login_provider"] = "kakao"

            flash("탈퇴한 계정이 복구되었습니다.")
            return redirect(url_for("index"))

        flash("이미 가입된 이메일입니다. 기존 방식으로 로그인해주세요.")
        return redirect(url_for("login"))

    create_social_user(
        nickname=nickname,
        email=email,
        provider="kakao",
        social_id=social_id,
        profile_image_url=profile_image_url,
    )

    user = find_user_by_social("kakao", social_id)

    session["user_email"] = user["email"]
    session["user_nickname"] = user["nickname"]
    session["user_id"] = user["user_id"]
    session["role"] = user.get("role", "USER")
    session["login_provider"] = "kakao"

    flash("카카오 로그인 성공")
    return redirect(url_for("index"))


# =========================
# 네이버 로그인 요청
# =========================
@app.route("/login/naver")
def login_naver():
    client_id = os.getenv("NAVER_CLIENT_ID")
    redirect_uri = os.getenv("NAVER_REDIRECT_URI")

    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    auth_url = (
        "https://nid.naver.com/oauth2.0/authorize"
        f"?response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )
    return redirect(auth_url)


# =========================
# 네이버 로그인 콜백
# =========================
@app.route("/login/naver/callback")
def login_naver_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        flash("네이버 로그인에 실패했습니다.")
        return redirect(url_for("login"))

    if state != session.get("oauth_state"):
        flash("잘못된 요청입니다.")
        return redirect(url_for("login"))

    token_res = requests.post(
        "https://nid.naver.com/oauth2.0/token",
        params={
            "grant_type": "authorization_code",
            "client_id": os.getenv("NAVER_CLIENT_ID"),
            "client_secret": os.getenv("NAVER_CLIENT_SECRET"),
            "code": code,
            "state": state,
        },
    )

    token_json = token_res.json()
    access_token = token_json.get("access_token")

    if not access_token:
        flash(f"네이버 토큰 발급 실패: {token_json}")
        return redirect(url_for("login"))

    user_res = requests.get(
        "https://openapi.naver.com/v1/nid/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    user_json = user_res.json()
    response = user_json.get("response", {})

    social_id = str(response.get("id"))
    email = response.get("email")
    if not email:
        email = f"naver_{social_id}@naver.local"

    nickname = response.get("nickname") or response.get("name") or f"naver_{social_id}"
    profile_image_url = response.get("profile_image")

    user = find_user_by_social("naver", social_id)

    if user:
        session["user_email"] = user["email"]
        session["user_nickname"] = user["nickname"]
        session["user_id"] = user["user_id"]
        session["role"] = user.get("role", "USER")
        session["login_provider"] = "naver"
        flash("네이버 로그인 성공")
        return redirect(url_for("index"))

    existing_user = find_user_by_email(email)

    if existing_user:
        if existing_user.get("status") == "DELETED":
            restore_user(existing_user["user_id"])
            user = find_user_by_email(email)

            session["user_email"] = user["email"]
            session["user_nickname"] = user["nickname"]
            session["user_id"] = user["user_id"]
            session["role"] = user.get("role", "USER")
            session["login_provider"] = "naver"

            flash("탈퇴한 계정이 복구되었습니다.")
            return redirect(url_for("index"))

        flash("이미 가입된 이메일입니다. 기존 방식으로 로그인해주세요.")
        return redirect(url_for("login"))

    create_social_user(
        nickname=nickname,
        email=email,
        provider="naver",
        social_id=social_id,
        profile_image_url=profile_image_url,
    )

    user = find_user_by_social("naver", social_id)

    session["user_email"] = user["email"]
    session["user_nickname"] = user["nickname"]
    session["user_id"] = user["user_id"]
    session["role"] = user.get("role", "USER")
    session["login_provider"] = "naver"

    flash("네이버 로그인 성공")
    return redirect(url_for("index"))


# =========================
# 구글 로그인 요청
# =========================
@app.route("/login/google")
def login_google():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    scope = "openid email profile"

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope}"
        f"&state={state}"
        f"&access_type=offline"
        f"&prompt=select_account"
    )
    return redirect(auth_url)


# =========================
# 구글 로그인 콜백
# =========================
@app.route("/login/google/callback")
def login_google_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        flash("구글 로그인에 실패했습니다.")
        return redirect(url_for("login"))

    if state != session.get("oauth_state"):
        flash("잘못된 요청입니다.")
        return redirect(url_for("login"))

    token_data = {
        "code": code,
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "grant_type": "authorization_code",
    }

    token_res = requests.post(
        "https://oauth2.googleapis.com/token",
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    token_json = token_res.json()
    access_token = token_json.get("access_token")

    if not access_token:
        flash(f"구글 토큰 발급 실패: {token_json}")
        return redirect(url_for("login"))

    user_res = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    user_json = user_res.json()

    social_id = str(user_json.get("id"))
    email = user_json.get("email")
    if not email:
        email = f"google_{social_id}@google.local"

    nickname = user_json.get("name") or user_json.get("given_name") or f"google_{social_id}"
    profile_image_url = user_json.get("picture")

    user = find_user_by_social("google", social_id)

    if user:
        session["user_email"] = user["email"]
        session["user_nickname"] = user["nickname"]
        session["user_id"] = user["user_id"]
        session["role"] = user.get("role", "USER")
        session["login_provider"] = "google"
        flash("구글 로그인 성공")
        return redirect(url_for("index"))

    existing_user = find_user_by_email(email)

    if existing_user:
        if existing_user.get("status") == "DELETED":
            restore_user(existing_user["user_id"])
            user = find_user_by_email(email)

            session["user_email"] = user["email"]
            session["user_nickname"] = user["nickname"]
            session["user_id"] = user["user_id"]
            session["role"] = user.get("role", "USER")
            session["login_provider"] = "google"

            flash("탈퇴한 계정이 복구되었습니다.")
            return redirect(url_for("index"))

        flash("이미 가입된 이메일입니다. 기존 방식으로 로그인해주세요.")
        return redirect(url_for("login"))

    create_social_user(
        nickname=nickname,
        email=email,
        provider="google",
        social_id=social_id,
        profile_image_url=profile_image_url,
    )

    user = find_user_by_social("google", social_id)

    session["user_email"] = user["email"]
    session["user_nickname"] = user["nickname"]
    session["user_id"] = user["user_id"]
    session["role"] = user.get("role", "USER")
    session["login_provider"] = "google"

    flash("구글 로그인 성공")
    return redirect(url_for("index"))


# =========================
# 마이페이지
# =========================
@app.route("/mypage")
@login_required
def mypage():
    return render_template(
        "mypage/mypage.html",
        user_nickname=session.get("user_nickname"),
        user_email=session.get("user_email"),
    )


# =========================
# 닉네임 변경
# =========================
@app.route("/mypage/nickname", methods=["POST"])
@login_required
def update_nickname():
    user_id = session["user_id"]
    current_nickname = session.get("user_nickname", "")
    new_nickname = request.form.get("nickname", "").strip()

    if not new_nickname:
        flash("닉네임을 입력해주세요.")
        return redirect(url_for("mypage"))

    if len(new_nickname) < 2 or len(new_nickname) > 12:
        flash("닉네임은 2자 이상 12자 이하로 입력해주세요.")
        return redirect(url_for("mypage"))

    if new_nickname == current_nickname:
        flash("현재 사용 중인 닉네임입니다.")
        return redirect(url_for("mypage"))

    existing_user = find_user_by_nickname(new_nickname)
    if existing_user and existing_user["user_id"] != user_id:
        flash("이미 사용 중인 닉네임입니다.")
        return redirect(url_for("mypage"))

    success = update_user_nickname(user_id, new_nickname)

    if success:
        session["user_nickname"] = new_nickname
        flash("닉네임이 변경되었습니다.")
    else:
        flash("닉네임 변경에 실패했습니다.")

    return redirect(url_for("mypage"))


# =========================
# 내 리뷰 보기
# =========================
@app.route("/mypage/reviews")
@login_required
def mypage_reviews():
    user_id = session["user_id"]
    reviews = fetch_my_reviews(user_id)

    return render_template(
        "mypage/mypage_reviews.html",
        reviews=reviews,
        user_nickname=session.get("user_nickname"),
    )


# =========================
# 즐겨찾기 보기
# =========================
@app.route("/mypage/favorites")
@login_required
def mypage_favorites():
    user_id = session["user_id"]
    favorites = fetch_my_favorites(user_id)

    return render_template(
        "mypage/mypage_favorites.html",
        favorites=favorites,
        user_nickname=session.get("user_nickname"),
    )


# =========================
# 방문 기록 보기
# =========================
@app.route("/mypage/visits")
@login_required
def mypage_visits():
    user_id = session["user_id"]
    visits = fetch_my_visits(user_id)

    return render_template(
        "mypage/mypage_visits.html",
        visits=visits,
        user_nickname=session.get("user_nickname"),
    )


# =========================
# 업적 / 랭킹 보기
# =========================
@app.route("/mypage/achievements")
@login_required
def mypage_achievements():
    user_id = session["user_id"]
    achievements = fetch_my_achievements(user_id)

    return render_template(
        "mypage/mypage_achievements.html",
        achievements=achievements,
        user_nickname=session.get("user_nickname"),
    )


# =========================
# 회원탈퇴
# =========================
@app.route("/withdraw", methods=["POST"])
def withdraw():
    if "user_id" not in session:
        flash("로그인이 필요합니다.")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    withdraw_user(user_id)
    session.clear()

    flash("회원탈퇴가 완료되었습니다.")
    return redirect(url_for("index"))


# =========================
# 관리자 페이지
# =========================
@app.route("/admin")
@admin_required
def admin_page():
    return render_template("admin/admin_dashboard.html")


# =========================
# 관리자 회원 관리
# =========================
@app.route("/admin/users")
@admin_required
def admin_users():
    users = fetch_all_users()
    return render_template("admin/admin_users.html", users=users)


# =========================
# 관리자 회원 비활성화
# =========================
@app.route("/admin/users/<int:user_id>/deactivate", methods=["POST"])
@admin_required
def admin_user_deactivate(user_id):
    admin_deactivate_user(user_id)
    flash("회원 상태를 DELETED로 변경했습니다.")
    return redirect(url_for("admin_users"))


# =========================
# 관리자 회원 복구
# =========================
@app.route("/admin/users/<int:user_id>/restore", methods=["POST"])
@admin_required
def admin_user_restore(user_id):
    admin_restore_user(user_id)
    flash("회원 상태를 ACTIVE로 복구했습니다.")
    return redirect(url_for("admin_users"))


# =========================
# 관리자 리뷰 관리 목록
# =========================
@app.route("/admin/reviews")
@admin_required
def admin_reviews():
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "").strip()

    reviews = fetch_admin_reviews(keyword=keyword, status=status)

    return render_template(
        "admin/admin_reviews.html",
        reviews=reviews,
        keyword=keyword,
        status=status,
    )


# =========================
# 리뷰 숨김 처리
# =========================
@app.route("/admin/reviews/<int:review_id>/hide", methods=["POST"])
@admin_required
def admin_hide_review(review_id):
    success = update_admin_review_status(review_id, "HIDDEN")
    if success:
        flash("리뷰를 숨김 처리했습니다.")
    else:
        flash("리뷰를 찾을 수 없습니다.")
    return redirect(url_for("admin_reviews"))


# =========================
# 리뷰 삭제 처리
# =========================
@app.route("/admin/reviews/<int:review_id>/delete", methods=["POST"])
@admin_required
def admin_delete_review(review_id):
    success = update_admin_review_status(review_id, "DELETED")
    if success:
        flash("리뷰를 삭제 처리했습니다.")
    else:
        flash("리뷰를 찾을 수 없습니다.")
    return redirect(url_for("admin_reviews"))


# =========================
# 리뷰 복구 처리
# =========================
@app.route("/admin/reviews/<int:review_id>/restore", methods=["POST"])
@admin_required
def admin_restore_review(review_id):
    success = update_admin_review_status(review_id, "ACTIVE")
    if success:
        flash("리뷰를 복구했습니다.")
    else:
        flash("리뷰를 찾을 수 없습니다.")
    return redirect(url_for("admin_reviews"))


# =========================
# 관리자 신고 관리 목록
# =========================
@app.route("/admin/reports")
@admin_required
def admin_reports():
    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "").strip()

    reports = fetch_admin_reports(keyword=keyword, status=status)

    return render_template(
        "admin/admin_reports.html",
        reports=reports,
        keyword=keyword,
        status=status,
    )


# =========================
# 신고 승인 처리
# =========================
@app.route("/admin/reports/<int:report_id>/resolve", methods=["POST"])
@admin_required
def admin_resolve_report(report_id):
    success = update_admin_report_status(report_id, "RESOLVED")
    if success:
        flash("신고를 처리 완료 상태로 변경했습니다.")
    else:
        flash("신고 내역을 찾을 수 없습니다.")
    return redirect(url_for("admin_reports"))


# =========================
# 신고 반려 처리
# =========================
@app.route("/admin/reports/<int:report_id>/reject", methods=["POST"])
@admin_required
def admin_reject_report(report_id):
    success = update_admin_report_status(report_id, "REJECTED")
    if success:
        flash("신고를 반려 처리했습니다.")
    else:
        flash("신고 내역을 찾을 수 없습니다.")
    return redirect(url_for("admin_reports"))


# =========================
# 관리자 제재 관리
# =========================
@app.route("/admin/sanctions", methods=["GET", "POST"])
@admin_required
def admin_sanctions():
    if request.method == "POST":
        user_nickname = request.form.get("user_nickname", "").strip()
        sanction_type = request.form.get("sanction_type", "").strip()
        reason = request.form.get("reason", "").strip()
        expire_at = request.form.get("expire_at", "").strip()

        if not user_nickname or not sanction_type or not reason:
            flash("대상 닉네임, 제재 종류, 사유를 입력해주세요.")
            return redirect(url_for("admin_sanctions"))

        create_admin_sanction(
            user_nickname=user_nickname,
            sanction_type=sanction_type,
            reason=reason,
            expire_at=expire_at if expire_at else "-"
        )
        flash("제재가 등록되었습니다.")
        return redirect(url_for("admin_sanctions"))

    keyword = request.args.get("keyword", "").strip()
    status = request.args.get("status", "").strip()

    sanctions = fetch_admin_sanctions(keyword=keyword, status=status)

    return render_template(
        "admin/admin_sanctions.html",
        sanctions=sanctions,
        keyword=keyword,
        status=status,
    )


# =========================
# 제재 해제
# =========================
@app.route("/admin/sanctions/<int:sanction_id>/release", methods=["POST"])
@admin_required
def admin_release_sanction(sanction_id):
    success = release_admin_sanction(sanction_id)
    if success:
        flash("제재를 해제했습니다.")
    else:
        flash("제재 내역을 찾을 수 없습니다.")
    return redirect(url_for("admin_sanctions"))



# =========================
# 서버 실행
# =========================
if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "True") == "True")