# =========================
# Flask 기본 기능 import
# =========================
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify

# =========================
# 외부 라이브러리 / 기본 라이브러리 import
# =========================
import os
import requests
import secrets
import random
import time

# =========================
# 메일 전송용 import
# =========================
from flask_mail import Message
from .extensions import mail

# =========================
# 로그인 관련 DB 함수 import
# =========================
from .login_db import (
    verify_user_login,              # 일반 로그인 검증
    create_user,                    # 일반 회원가입
    find_user_by_email,             # 이메일로 회원 조회
    find_user_by_social,            # 소셜 계정으로 회원 조회
    create_social_user_with_form,   # 소셜 회원가입 저장
    withdraw_user,                  # 회원 탈퇴
    find_user_by_nickname,          # 닉네임 중복 확인
    find_email_by_nickname,         # 닉네임으로 이메일 찾기
    reset_user_password,            # 비밀번호 재설정
)

# =========================
# Blueprint 생성
# =========================
login_bp = Blueprint("login", __name__)


# =========================
# 비밀번호 재설정용 인증 세션 초기화
# =========================
def clear_reset_session():
    session.pop("reset_code", None)
    session.pop("reset_email", None)
    session.pop("reset_code_expire", None)
    session.pop("reset_verified", None)


# =========================
# 일반 로그인
# GET  : 로그인 페이지 보여주기
# POST : 이메일 / 비밀번호 검사 후 로그인 처리
# =========================
@login_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("이메일과 비밀번호를 입력해주세요.")
            return redirect(url_for("login.login"))

        user = verify_user_login(email, password)

        if user:
            session["user_email"] = user["email"]
            session["user_nickname"] = user["nickname"]
            session["user_id"] = user["user_id"]
            session["role"] = user.get("role", "USER")
            session["login_provider"] = "local"
            return redirect(url_for("index"))

        flash("이메일 또는 비밀번호가 올바르지 않거나 탈퇴한 계정입니다.")
        return redirect(url_for("login.login"))

    return render_template("login/login.html")


# =========================
# 일반 회원가입
# GET  : 회원가입 페이지 보여주기
# POST : 회원가입 데이터 검증 후 저장
# =========================
@login_bp.route("/signup", methods=["GET", "POST"])
def signup():
    # 일반 회원가입으로 들어오면 이전 소셜 회원가입 임시 데이터 제거
    if request.method == "GET":
        mode = request.args.get("mode", "").strip()
        if mode == "local":
            session.pop("social_signup_data", None)

    # 소셜 회원가입 중이면 세션에 저장된 값 가져오기
    social_data = session.get("social_signup_data", {})

    if request.method == "POST":
        # 기본 회원 정보
        nickname = request.form.get("nickname", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        password_confirm = request.form.get("password_confirm", "").strip()

        # 추가 정보
        gender = request.form.get("gender", "").strip()
        birth_year = request.form.get("birth_year", "").strip()
        birth_month = request.form.get("birth_month", "").strip()
        birth_day = request.form.get("birth_day", "").strip()

        # 주소 정보
        postcode = request.form.get("postcode", "").strip()
        road_address = request.form.get("roadAddress", "").strip()
        jibun_address = request.form.get("jibunAddress", "").strip()
        detail_address = request.form.get("detailAddress", "").strip()
        extra_address = request.form.get("extraAddress", "").strip()

        # 광고 수신 동의
        ad_agree = request.form.get("ad_agree", "")

        # 이메일 / 닉네임 중복확인 여부
        email_checked = request.form.get("email_checked", "false")
        checked_email_value = request.form.get("checked_email_value", "").strip()
        nickname_checked = request.form.get("nickname_checked", "false")
        checked_nickname_value = request.form.get("checked_nickname_value", "").strip()

        # 에러 시 다시 채워줄 값들
        form_data = {
            "email": email,
            "nickname": nickname,
            "gender": gender,
            "birth_year": birth_year,
            "birth_month": birth_month,
            "birth_day": birth_day,
            "postcode": postcode,
            "roadAddress": road_address,
            "jibunAddress": jibun_address,
            "detailAddress": detail_address,
            "extraAddress": extra_address,
            "ad_agree": ad_agree,
        }

        # 회원가입 에러 시 회원가입 페이지로 다시 보내는 내부 함수
        def render_signup_with_error(message):
            flash(message)
            return render_template("login/signup.html", social_data=social_data, form_data=form_data)

        # 필수 입력값 검사
        if not nickname or not email:
            return render_signup_with_error("이메일과 닉네임을 입력해주세요.")
        if not gender:
            return render_signup_with_error("성별을 선택해주세요.")
        if not birth_year or not birth_month or not birth_day:
            return render_signup_with_error("생년월일을 입력해주세요.")
        if not postcode or not road_address:
            return render_signup_with_error("주소 검색을 통해 주소를 입력해주세요.")

        # 이메일 중복 검사
        existing_user = find_user_by_email(email)
        if existing_user:
            if not social_data or existing_user["email"] != social_data.get("email"):
                return render_signup_with_error("이미 가입된 이메일입니다.")

        # 닉네임 중복 검사
        existing_nickname = find_user_by_nickname(nickname)
        if existing_nickname:
            if not social_data or existing_nickname["nickname"] != social_data.get("nickname"):
                return render_signup_with_error("이미 사용 중인 닉네임입니다.")

        # =========================
        # 소셜 회원가입 처리
        # =========================
        if social_data:
            provider = social_data.get("provider")
            social_id = social_data.get("social_id")
            profile_image_url = social_data.get("profile_image_url")

            if not provider or not social_id:
                flash("소셜 회원가입 정보가 올바르지 않습니다. 다시 시도해주세요.")
                session.pop("social_signup_data", None)
                return redirect(url_for("login.login"))

            if not password or not password_confirm:
                return render_signup_with_error("비밀번호와 비밀번호 확인을 입력해주세요.")

            if password != password_confirm:
                return render_signup_with_error("비밀번호와 비밀번호 확인이 일치하지 않습니다.")

            if nickname_checked != "true" or checked_nickname_value != nickname:
                return render_signup_with_error("닉네임 중복 확인을 해주세요.")

            create_social_user_with_form(
                nickname=nickname,
                email=email,
                password=password,
                provider=provider,
                social_id=social_id,
                profile_image_url=profile_image_url,
            )

            user = find_user_by_social(provider, social_id)
            if not user:
                return render_signup_with_error("소셜 회원가입 후 사용자 조회에 실패했습니다.")

            session["user_email"] = user["email"]
            session["user_nickname"] = user["nickname"]
            session["user_id"] = user["user_id"]
            session["role"] = user.get("role", "USER")
            session["login_provider"] = provider.lower()

            session.pop("social_signup_data", None)

            flash("간편 회원가입이 완료되었습니다.")
            return redirect(url_for("index"))

        # =========================
        # 일반 회원가입 처리
        # =========================
        if not password or not password_confirm:
            return render_signup_with_error("비밀번호와 비밀번호 확인을 입력해주세요.")

        if password != password_confirm:
            return render_signup_with_error("비밀번호와 비밀번호 확인이 일치하지 않습니다.")

        if email_checked != "true" or checked_email_value != email:
            return render_signup_with_error("이메일 중복 확인을 해주세요.")

        if nickname_checked != "true" or checked_nickname_value != nickname:
            return render_signup_with_error("닉네임 중복 확인을 해주세요.")

        create_user(nickname, email, password)
        flash("회원가입이 완료되었습니다. 로그인해주세요.")
        return redirect(url_for("login.login"))

    return render_template("login/signup.html", social_data=social_data, form_data={})


# =========================
# 회원가입 초기화
# 소셜 회원가입 임시 데이터를 제거하고 일반 회원가입 화면으로 이동
# =========================
@login_bp.route("/signup/reset")
def signup_reset():
    session.pop("social_signup_data", None)
    return redirect(url_for("login.signup", mode="local"))


# =========================
# 이메일 / 닉네임 중복확인 API
# 비동기 중복 체크용
# =========================
@login_bp.route("/api/check-duplicate")
def check_duplicate():
    check_type = request.args.get("type", "").strip()
    value = request.args.get("value", "").strip()

    if not value:
        return jsonify({"available": False, "message": "값을 입력해주세요."})

    if check_type == "email":
        user = find_user_by_email(value)
        return jsonify({
            "available": not bool(user),
            "message": "사용 가능한 이메일입니다." if not user else "이미 사용 중인 이메일입니다."
        })

    if check_type == "nickname":
        user = find_user_by_nickname(value)
        return jsonify({
            "available": not bool(user),
            "message": "사용 가능한 닉네임입니다." if not user else "이미 사용 중인 닉네임입니다."
        })

    return jsonify({"available": False, "message": "잘못된 요청입니다."})


# =========================
# 아이디 찾기
# 닉네임으로 이메일 찾기
# =========================
@login_bp.route("/find-id", methods=["GET", "POST"])
def find_id():
    found_email = None

    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()

        if not nickname:
            flash("닉네임을 입력해주세요.")
            return redirect(url_for("login.find_id"))

        user = find_email_by_nickname(nickname)
        if not user:
            flash("일치하는 회원 정보를 찾을 수 없습니다.")
            return redirect(url_for("login.find_id"))

        found_email = user["email"]

    return render_template("login/find_id.html", found_email=found_email)


# =========================
# 비밀번호 재설정 인증번호 메일 발송
# 이메일이 가입된 계정인지 확인 후 6자리 인증번호 전송
# 인증번호 유효시간은 3분
# =========================
@login_bp.route("/login/send-reset-code", methods=["POST"])
def send_reset_code():
    email = request.form.get("email", "").strip()

    if not email:
        return jsonify({"success": False, "message": "이메일을 입력해주세요."})

    user = find_user_by_email(email)
    if not user:
        return jsonify({"success": False, "message": "가입된 이메일이 아닙니다."})

    code = str(random.randint(100000, 999999))

    clear_reset_session()
    session["reset_code"] = code
    session["reset_email"] = email
    session["reset_code_expire"] = time.time() + 180
    session["reset_verified"] = False

    try:
        msg = Message(
            subject="[흑백로그] 비밀번호 재설정 인증번호",
            recipients=[email],
            body=f"""흑백로그 비밀번호 재설정 인증번호는 {code} 입니다.

3분 이내에 입력해주세요.
인증시간이 지나면 다시 인증번호를 요청해야 합니다."""
        )
        mail.send(msg)
        return jsonify({"success": True, "message": "인증번호를 이메일로 전송했습니다."})
    except Exception as e:
        return jsonify({"success": False, "message": f"메일 전송 실패: {str(e)}"})


# =========================
# 인증번호 확인
# 입력한 인증번호가 맞고 3분 이내인지 검사
# =========================
@login_bp.route("/login/verify-reset-code", methods=["POST"])
def verify_reset_code():
    email = request.form.get("email", "").strip()
    code = request.form.get("code", "").strip()

    saved_code = session.get("reset_code")
    saved_email = session.get("reset_email")
    expire_time = session.get("reset_code_expire")

    if not saved_code or not saved_email or not expire_time:
        return jsonify({"success": False, "message": "인증번호를 먼저 발송해주세요."})

    if time.time() > expire_time:
        clear_reset_session()
        return jsonify({"success": False, "message": "인증시간이 만료되었습니다. 다시 요청해주세요."})

    if email != saved_email:
        return jsonify({"success": False, "message": "인증번호를 받은 이메일과 일치하지 않습니다."})

    if code != saved_code:
        return jsonify({"success": False, "message": "인증번호가 올바르지 않습니다."})

    session["reset_verified"] = True
    return jsonify({"success": True, "message": "이메일 인증이 완료되었습니다."})


# =========================
# 비밀번호 찾기 / 재설정
# 이메일 인증 완료 후에만 비밀번호 변경 가능
# =========================
@login_bp.route("/find-password", methods=["GET", "POST"])
def find_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        new_password = request.form.get("new_password", "").strip()
        new_password_confirm = request.form.get("new_password_confirm", "").strip()

        if not email or not new_password or not new_password_confirm:
            flash("모든 항목을 입력해주세요.")
            return redirect(url_for("login.find_password"))

        if session.get("reset_verified") is not True:
            flash("이메일 인증을 먼저 완료해주세요.")
            return redirect(url_for("login.find_password"))

        if session.get("reset_email") != email:
            flash("인증한 이메일과 입력한 이메일이 일치하지 않습니다.")
            return redirect(url_for("login.find_password"))

        expire_time = session.get("reset_code_expire")
        if not expire_time or time.time() > expire_time:
            clear_reset_session()
            flash("인증시간이 만료되었습니다. 다시 인증해주세요.")
            return redirect(url_for("login.find_password"))

        if new_password != new_password_confirm:
            flash("새 비밀번호가 일치하지 않습니다.")
            return redirect(url_for("login.find_password"))

        if len(new_password) < 4:
            flash("비밀번호는 4자 이상 입력해주세요.")
            return redirect(url_for("login.find_password"))

        success = reset_user_password(email, new_password)
        if not success:
            flash("일치하는 회원을 찾을 수 없습니다.")
            return redirect(url_for("login.find_password"))

        clear_reset_session()
        flash("비밀번호가 재설정되었습니다. 다시 로그인해주세요.")
        return redirect(url_for("login.login"))

    return render_template("login/find_password.html")

# =========================
# 메일 전송 테스트
# 브라우저에서 /login/test-mail 로 접속하면 메일 전송
# =========================
@login_bp.route("/login/test-mail")
def test_mail():
    try:
        test_recipient = os.getenv("MAIL_USERNAME")

        if not test_recipient:
            return "메일 전송 실패: MAIL_USERNAME 값이 없습니다."

        msg = Message(
            subject="[흑백로그] 메일 테스트",
            recipients=[test_recipient],
            body="흑백로그 메일 전송 테스트입니다."
        )
        mail.send(msg)
        return "메일 전송 성공"
    except Exception as e:
        return f"메일 전송 실패: {str(e)}"


# =========================
# 로그아웃
# provider 값에 따라 처리
# =========================
@login_bp.route("/logout")
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

    flash("로그아웃되었습니다.")
    return redirect(url_for("index"))


# =========================
# 카카오 로그아웃 콜백
# =========================
@login_bp.route("/logout/kakao/callback")
def logout_kakao_callback():
    flash("로그아웃되었습니다.")
    return redirect(url_for("index"))


# =========================
# 카카오 로그인 요청
# 카카오 인증 페이지로 이동
# =========================
@login_bp.route("/login/kakao")
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
# 카카오 인증 후 돌아왔을 때 실행
# =========================
@login_bp.route("/login/kakao/callback")
def login_kakao_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        flash("카카오 로그인에 실패했습니다.")
        return redirect(url_for("login.login"))

    if state != session.get("oauth_state"):
        flash("잘못된 요청입니다.")
        return redirect(url_for("login.login"))

    session.pop("oauth_state", None)

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
        return redirect(url_for("login.login"))

    user_res = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-type": "application/x-www-form-urlencoded;charset=utf-8",
        },
    )
    user_json = user_res.json()

    social_id = str(user_json.get("id"))
    kakao_account = user_json.get("kakao_account", {})
    profile = kakao_account.get("profile", {})

    email = kakao_account.get("email") or f"kakao_{social_id}@kakao.local"
    nickname = profile.get("nickname") or f"kakao_{social_id}"
    profile_image_url = profile.get("profile_image_url")

    if not social_id:
        flash("카카오 사용자 정보를 불러오지 못했습니다.")
        return redirect(url_for("login.login"))

    user = find_user_by_social("KAKAO", social_id)
    if user:
        session["user_email"] = user["email"]
        session["user_nickname"] = user["nickname"]
        session["user_id"] = user["user_id"]
        session["role"] = user.get("role", "USER")
        session["login_provider"] = "kakao"
        flash("로그인되었습니다.")
        return redirect(url_for("index"))

    session["social_signup_data"] = {
        "provider": "KAKAO",
        "social_id": social_id,
        "email": email,
        "nickname": nickname,
        "profile_image_url": profile_image_url,
    }
    flash("추가 회원정보를 입력해주세요.")
    return redirect(url_for("login.signup"))


# =========================
# 네이버 로그인 요청
# 네이버 인증 페이지로 이동
# =========================
@login_bp.route("/login/naver")
def login_naver():
    naver_client_id = os.getenv("NAVER_CLIENT_ID")
    redirect_uri = os.getenv("NAVER_REDIRECT_URI")

    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    auth_url = (
        "https://nid.naver.com/oauth2.0/authorize"
        f"?response_type=code"
        f"&client_id={naver_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )
    return redirect(auth_url)


# =========================
# 네이버 로그인 콜백
# =========================
@login_bp.route("/login/naver/callback")
def login_naver_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        flash("네이버 로그인에 실패했습니다.")
        return redirect(url_for("login.login"))

    if state != session.get("oauth_state"):
        flash("잘못된 요청입니다.")
        return redirect(url_for("login.login"))

    session.pop("oauth_state", None)

    token_data = {
        "grant_type": "authorization_code",
        "client_id": os.getenv("NAVER_CLIENT_ID"),
        "client_secret": os.getenv("NAVER_CLIENT_SECRET"),
        "code": code,
        "state": state,
    }
    token_res = requests.post("https://nid.naver.com/oauth2.0/token", params=token_data)
    token_json = token_res.json()
    access_token = token_json.get("access_token")

    if not access_token:
        flash(f"네이버 토큰 발급 실패: {token_json}")
        return redirect(url_for("login.login"))

    user_res = requests.get(
        "https://openapi.naver.com/v1/nid/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_json = user_res.json().get("response", {})

    social_id = user_json.get("id")
    email = user_json.get("email") or f"naver_{social_id}@naver.local"
    nickname = user_json.get("nickname") or f"naver_{social_id}"
    profile_image_url = user_json.get("profile_image")

    if not social_id:
        flash("네이버 사용자 정보를 불러오지 못했습니다.")
        return redirect(url_for("login.login"))

    user = find_user_by_social("NAVER", social_id)
    if user:
        session["user_email"] = user["email"]
        session["user_nickname"] = user["nickname"]
        session["user_id"] = user["user_id"]
        session["role"] = user.get("role", "USER")
        session["login_provider"] = "naver"
        flash("로그인되었습니다.")
        return redirect(url_for("index"))

    session["social_signup_data"] = {
        "provider": "NAVER",
        "social_id": social_id,
        "email": email,
        "nickname": nickname,
        "profile_image_url": profile_image_url,
    }
    flash("추가 회원정보를 입력해주세요.")
    return redirect(url_for("login.signup"))


# =========================
# 구글 로그인 요청
# 구글 인증 페이지로 이동
# =========================
@login_bp.route("/login/google")
def login_google():
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={google_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&state={state}"
    )
    return redirect(auth_url)


# =========================
# 구글 로그인 콜백
# =========================
@login_bp.route("/login/google/callback")
def login_google_callback():
    code = request.args.get("code")
    state = request.args.get("state")

    if not code:
        flash("구글 로그인에 실패했습니다.")
        return redirect(url_for("login.login"))

    if state != session.get("oauth_state"):
        flash("잘못된 요청입니다.")
        return redirect(url_for("login.login"))

    session.pop("oauth_state", None)

    token_data = {
        "code": code,
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "grant_type": "authorization_code",
    }
    token_res = requests.post("https://oauth2.googleapis.com/token", data=token_data)
    token_json = token_res.json()
    access_token = token_json.get("access_token")

    if not access_token:
        flash(f"구글 토큰 발급 실패: {token_json}")
        return redirect(url_for("login.login"))

    user_res = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_json = user_res.json()

    social_id = user_json.get("id")
    email = user_json.get("email") or f"google_{social_id}@google.local"
    nickname = user_json.get("name") or f"google_{social_id}"
    profile_image_url = user_json.get("picture")

    if not social_id:
        flash("구글 사용자 정보를 불러오지 못했습니다.")
        return redirect(url_for("login.login"))

    user = find_user_by_social("GOOGLE", social_id)
    if user:
        session["user_email"] = user["email"]
        session["user_nickname"] = user["nickname"]
        session["user_id"] = user["user_id"]
        session["role"] = user.get("role", "USER")
        session["login_provider"] = "google"
        flash("로그인되었습니다.")
        return redirect(url_for("index"))

    session["social_signup_data"] = {
        "provider": "GOOGLE",
        "social_id": social_id,
        "email": email,
        "nickname": nickname,
        "profile_image_url": profile_image_url,
    }
    flash("추가 회원정보를 입력해주세요.")
    return redirect(url_for("login.signup"))


# =========================
# 회원 탈퇴
# 로그인된 사용자만 가능
# =========================
@login_bp.route("/withdraw", methods=["POST"])
def withdraw():
    user_id = session.get("user_id")

    if not user_id:
        flash("로그인이 필요합니다.")
        return redirect(url_for("login.login"))

    withdraw_user(user_id)
    session.clear()
    flash("회원 탈퇴가 완료되었습니다.")
    return redirect(url_for("index"))