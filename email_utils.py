# email_utils.py
import smtplib
import os
from email.mime.text import MIMEText

def send_password_reset_email(to_email, reset_link):
    EMAIL_USER = os.getenv("EMAIL_USER")
    EMAIL_PASS = os.getenv("EMAIL_PASS")

    subject = "Cricket Stats Pack - Password Reset"
    body = f"""
    Hi there,

    A request was made to reset your Cricket Stats Pack password.

    Click the link below to reset your password:
    {reset_link}

    If you didn’t request this, you can safely ignore it.

    Cheers,
    Cricket Stats Pack Team
    """

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
            print(f"✅ Reset email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
