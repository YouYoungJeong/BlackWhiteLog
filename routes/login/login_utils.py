import os
import random
import smtplib
from email.message import EmailMessage


def generate_verification_code():
    return str(random.randint(100000, 999999))


def send_verification_email(to_email, code):
    smtp_host = os.getenv("MAIL_SERVER")
    smtp_port = int(os.getenv("MAIL_PORT", 587))
    smtp_user = os.getenv("MAIL_USERNAME")
    smtp_pass = os.getenv("MAIL_PASSWORD")
    mail_from = os.getenv("MAIL_DEFAULT_SENDER", smtp_user)

    msg = EmailMessage()
    msg["Subject"] = "[흑백로그] 비밀번호 재설정 인증번호"
    msg["From"] = mail_from
    msg["To"] = to_email
    msg.set_content(
        f"""흑백로그 비밀번호 재설정 인증번호는 {code} 입니다.

3분 이내에 입력해주세요.
인증시간이 지나면 다시 인증번호를 요청해야 합니다."""
    )

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)