# Flask 기본 기능들 import
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, session

# .env 파일에 저장한 환경변수 불러오기
from dotenv import load_dotenv

# 운영체제 환경변수 접근용
import os

# 외부 API 요청용
import requests

# OAuth state 값 생성용 (보안)
import secrets


# db.py 에서 필요한 함수들 import
from db import (
    fetch_categories,      # 카테고리 목록 조회
    fetch_regions,         # 지역 목록 조회
    fetch_restaurants,     # 음식점 목록 조회
    verify_user_login,     # 일반 로그인 검증
    create_user,           # 일반 회원가입
    find_user_by_email,    # 이메일로 회원 조회
    find_user_by_social,   # 소셜(provider + social_id)로 회원 조회
    create_social_user,    # 소셜 회원 생성
    withdraw_user,
    restore_user,
)


# .env 파일 로드
load_dotenv()

# Flask 앱 생성
app = Flask(__name__)

# 세션/flash 메시지용 비밀키 설정
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")


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


# =========================
# 일반 로그인
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    # POST 요청이면 로그인 처리
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # 이메일/비밀번호 검증
        user = verify_user_login(email, password)

        # 로그인 성공 시 세션 저장
        if user:
            session["user_email"] = user["email"]
            session["user_nickname"] = user["nickname"]
            session["user_id"] = user["user_id"]
            session["login_provider"] = "local"   # 일반 로그인 표시
            return redirect(url_for("index"))
        else:
            # 실패 시 에러 메시지
            flash("이메일 또는 비밀번호가 올바르지 않거나 탈퇴한 계정입니다.")
            return redirect(url_for("login"))

    # GET 요청이면 로그인 페이지 보여주기
    return render_template("login.html")


# =========================
# 일반 회원가입
# =========================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    # POST 요청이면 회원가입 처리
    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        # 입력값 검증
        if not nickname or not email or not password:
            flash("모든 값을 입력해주세요.")
            return redirect(url_for("signup"))

        # 이메일 중복 확인
        existing_user = find_user_by_email(email)
        if existing_user:
            flash("이미 가입된 이메일입니다.")
            return redirect(url_for("signup"))

        # 회원 생성
        create_user(nickname, email, password)

        # 회원가입 완료 후 로그인 페이지로 이동
        flash("회원가입이 완료되었습니다. 로그인해주세요.")
        return redirect(url_for("login"))

    # GET 요청이면 회원가입 페이지 보여주기
    return render_template("signup.html")


# =========================
# 아이디 찾기 / 비밀번호 찾기 페이지
# =========================
@app.route("/find-id")
def find_id():
    return render_template("find_id.html")


@app.route("/find-password")
def find_password():
    return render_template("find_password.html")


# =========================
# 로그아웃
# =========================
@app.route("/logout")
def logout():
    # 어떤 방식으로 로그인했는지 확인
    provider = session.get("login_provider")

    # 우리 사이트 세션 정보 먼저 삭제
    session.clear()

    # -------------------------
    # 카카오 로그아웃
    # -------------------------
    if provider == "kakao":
        kakao_rest_api_key = os.getenv("KAKAO_REST_API_KEY")
        kakao_logout_redirect_uri = os.getenv("KAKAO_LOGOUT_REDIRECT_URI")

        # 카카오 서버 로그아웃 URL
        logout_url = (
            "https://kauth.kakao.com/oauth/logout"
            f"?client_id={kakao_rest_api_key}"
            f"&logout_redirect_uri={kakao_logout_redirect_uri}"
        )
        return redirect(logout_url)

    # -------------------------
    # 네이버 로그아웃
    # -------------------------
    # 네이버는 카카오처럼 완전한 외부 로그아웃 제어가 제한적이라
    # 우리 서비스 세션만 끊는 방식이 일반적
    elif provider == "naver":
        flash("로그아웃되었습니다.")
        return redirect(url_for("index"))

    # -------------------------
    # 구글 로그아웃
    # -------------------------
    # 구글도 보통 우리 서비스 세션만 종료
    # 구글 계정 자체 로그아웃까지 강제하진 않는 경우가 많음
    elif provider == "google":
        flash("로그아웃되었습니다.")
        return redirect(url_for("index"))

    # -------------------------
    # 일반 로그인(local) 로그아웃
    # -------------------------
    else:
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

    # CSRF 방지용 state 생성
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    # 카카오 인가 코드 요청 URL 생성
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
    # 카카오가 넘겨준 인가 코드 / state 받기
    code = request.args.get("code")
    state = request.args.get("state")

    # code 없으면 실패
    if not code:
        flash("카카오 로그인에 실패했습니다.")
        return redirect(url_for("login"))

    # state 검증
    if state != session.get("oauth_state"):
        flash("잘못된 요청입니다.")
        return redirect(url_for("login"))

    # 토큰 발급 요청 데이터
    token_data = {
        "grant_type": "authorization_code",
        "client_id": os.getenv("KAKAO_REST_API_KEY"),
        "redirect_uri": os.getenv("KAKAO_REDIRECT_URI"),
        "code": code,
    }

    # 카카오 client secret 이 있으면 함께 전송
    client_secret = os.getenv("KAKAO_CLIENT_SECRET")
    if client_secret:
        token_data["client_secret"] = client_secret

    # access token 요청
    token_res = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data=token_data,
        headers={"Content-type": "application/x-www-form-urlencoded;charset=utf-8"},
    )

    token_json = token_res.json()
    access_token = token_json.get("access_token")

    # 토큰 발급 실패 시
    if not access_token:
        flash(f"카카오 토큰 발급 실패: {token_json}")
        return redirect(url_for("login"))

    # 사용자 정보 요청
    user_res = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-type": "application/x-www-form-urlencoded;charset=utf-8",
        },
    )

    user_json = user_res.json()

    # 사용자 정보 파싱
    social_id = str(user_json["id"])
    kakao_account = user_json.get("kakao_account", {})
    profile = kakao_account.get("profile", {})

    email = kakao_account.get("email")
    if not email:
        email = f"kakao_{social_id}@kakao.local"

    nickname = profile.get("nickname") or f"kakao_{social_id}"
    profile_image_url = profile.get("profile_image_url")

    # 기존 소셜 회원인지 확인
    user = find_user_by_social("kakao", social_id)

    # 이미 카카오 계정으로 가입된 회원이면 바로 로그인
    if user:
        session["user_email"] = user["email"]
        session["user_nickname"] = user["nickname"]
        session["user_id"] = user["user_id"]
        session["login_provider"] = "kakao"
        flash("카카오 로그인 성공")
        return redirect(url_for("index"))

    # 같은 이메일의 기존 회원 확인
    existing_user = find_user_by_email(email)

    # 기존 이메일 회원이 있으면 처리
    if existing_user:
        # 탈퇴한 계정이면 복구 후 로그인 허용
        if existing_user.get("status") == "DELETED":
            restore_user(existing_user["user_id"])
            user = find_user_by_email(email)

            session["user_email"] = user["email"]
            session["user_nickname"] = user["nickname"]
            session["user_id"] = user["user_id"]
            session["login_provider"] = "kakao"

            flash("탈퇴한 계정이 복구되었습니다.")
            return redirect(url_for("index"))

        # 탈퇴 계정이 아닌데 같은 이메일이 이미 있으면 신규 생성 막기
        else:
            flash("이미 가입된 이메일입니다. 기존 방식으로 로그인해주세요.")
            return redirect(url_for("login"))

    # 없으면 신규 소셜 회원 생성
    create_social_user(
        nickname=nickname,
        email=email,
        provider="kakao",
        social_id=social_id,
        profile_image_url=profile_image_url,
    )

    # 생성된 회원 다시 조회
    user = find_user_by_social("kakao", social_id)

    # 세션 저장
    session["user_email"] = user["email"]
    session["user_nickname"] = user["nickname"]
    session["user_id"] = user["user_id"]
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

    # CSRF 방지용 state
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    # 네이버 인가 코드 요청 URL
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
    # 네이버가 넘겨준 인가 코드 / state 받기
    code = request.args.get("code")
    state = request.args.get("state")

    # code 없으면 실패
    if not code:
        flash("네이버 로그인에 실패했습니다.")
        return redirect(url_for("login"))

    # state 검증
    if state != session.get("oauth_state"):
        flash("잘못된 요청입니다.")
        return redirect(url_for("login"))

    # access token 요청
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

    # 토큰 발급 실패 시
    if not access_token:
        flash(f"네이버 토큰 발급 실패: {token_json}")
        return redirect(url_for("login"))

    # 사용자 정보 요청
    user_res = requests.get(
        "https://openapi.naver.com/v1/nid/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    user_json = user_res.json()
    response = user_json.get("response", {})

    # 사용자 정보 파싱
    social_id = str(response.get("id"))
    email = response.get("email")
    if not email:
        email = f"naver_{social_id}@naver.local"

    nickname = response.get("nickname") or response.get("name") or f"naver_{social_id}"
    profile_image_url = response.get("profile_image")

    # 기존 소셜 회원인지 확인
    user = find_user_by_social("naver", social_id)

    # 이미 네이버 계정으로 가입된 회원이면 바로 로그인
    if user:
        session["user_email"] = user["email"]
        session["user_nickname"] = user["nickname"]
        session["user_id"] = user["user_id"]
        session["login_provider"] = "naver"
        flash("네이버 로그인 성공")
        return redirect(url_for("index"))

    # 같은 이메일의 기존 회원 확인
    existing_user = find_user_by_email(email)

    # 기존 이메일 회원이 있으면 처리
    if existing_user:
        # 탈퇴한 계정이면 복구 후 로그인 허용
        if existing_user.get("status") == "DELETED":
            restore_user(existing_user["user_id"])
            user = find_user_by_email(email)

            session["user_email"] = user["email"]
            session["user_nickname"] = user["nickname"]
            session["user_id"] = user["user_id"]
            session["login_provider"] = "naver"

            flash("탈퇴한 계정이 복구되었습니다.")
            return redirect(url_for("index"))

        # 탈퇴 계정이 아닌데 같은 이메일이 이미 있으면 신규 생성 막기
        else:
            flash("이미 가입된 이메일입니다. 기존 방식으로 로그인해주세요.")
            return redirect(url_for("login"))

    # 없으면 신규 소셜 회원 생성
    create_social_user(
        nickname=nickname,
        email=email,
        provider="naver",
        social_id=social_id,
        profile_image_url=profile_image_url,
    )

    # 생성된 회원 다시 조회
    user = find_user_by_social("naver", social_id)

    # 세션 저장
    session["user_email"] = user["email"]
    session["user_nickname"] = user["nickname"]
    session["user_id"] = user["user_id"]
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

    # CSRF 방지용 state 생성
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    # scope: 어떤 정보까지 요청할지
    scope = "openid email profile"

    # 구글 인가 코드 요청 URL
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
# =========================
# 구글 로그인 콜백
# =========================
@app.route("/login/google/callback")
def login_google_callback():
    # 구글이 넘겨준 인가 코드 / state 받기
    code = request.args.get("code")
    state = request.args.get("state")

    # code 없으면 실패
    if not code:
        flash("구글 로그인에 실패했습니다.")
        return redirect(url_for("login"))

    # state 검증
    if state != session.get("oauth_state"):
        flash("잘못된 요청입니다.")
        return redirect(url_for("login"))

    # 토큰 발급 요청 데이터
    token_data = {
        "code": code,
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "grant_type": "authorization_code",
    }

    # access token 요청
    token_res = requests.post(
        "https://oauth2.googleapis.com/token",
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    token_json = token_res.json()
    access_token = token_json.get("access_token")

    # 토큰 발급 실패 시
    if not access_token:
        flash(f"구글 토큰 발급 실패: {token_json}")
        return redirect(url_for("login"))

    # 사용자 정보 요청
    user_res = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    user_json = user_res.json()

    # 사용자 정보 파싱
    social_id = str(user_json.get("id"))
    email = user_json.get("email")
    if not email:
        email = f"google_{social_id}@google.local"

    nickname = user_json.get("name") or user_json.get("given_name") or f"google_{social_id}"
    profile_image_url = user_json.get("picture")

    # 기존 소셜 회원인지 확인
    user = find_user_by_social("google", social_id)

    # 이미 구글 계정으로 가입된 회원이면 바로 로그인
    if user:
        session["user_email"] = user["email"]
        session["user_nickname"] = user["nickname"]
        session["user_id"] = user["user_id"]
        session["login_provider"] = "google"
        flash("구글 로그인 성공")
        return redirect(url_for("index"))

    # 같은 이메일의 기존 회원 확인
    existing_user = find_user_by_email(email)

    # 기존 이메일 회원이 있으면 처리
    if existing_user:
        # 탈퇴한 계정이면 복구 후 로그인 허용
        if existing_user.get("status") == "DELETED":
            restore_user(existing_user["user_id"])
            user = find_user_by_email(email)

            session["user_email"] = user["email"]
            session["user_nickname"] = user["nickname"]
            session["user_id"] = user["user_id"]
            session["login_provider"] = "google"

            flash("탈퇴한 계정이 복구되었습니다.")
            return redirect(url_for("index"))

        # 탈퇴 계정이 아닌데 같은 이메일이 이미 있으면 신규 생성 막기
        else:
            flash("이미 가입된 이메일입니다. 기존 방식으로 로그인해주세요.")
            return redirect(url_for("login"))

    # 없으면 신규 소셜 회원 생성
    create_social_user(
        nickname=nickname,
        email=email,
        provider="google",
        social_id=social_id,
        profile_image_url=profile_image_url,
    )

    # 생성된 회원 다시 조회
    user = find_user_by_social("google", social_id)

    # 세션 저장
    session["user_email"] = user["email"]
    session["user_nickname"] = user["nickname"]
    session["user_id"] = user["user_id"]
    session["login_provider"] = "google"

    flash("구글 로그인 성공")
    return redirect(url_for("index"))
# =========================
# 마이페이지
# =========================
@app.route("/mypage")
def mypage():
    if "user_id" not in session:
        flash("로그인이 필요합니다.")
        return redirect(url_for("login"))

    return render_template("mypage.html")

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
# 서버 실행
# =========================
if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "True") == "True")