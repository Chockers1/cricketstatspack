# email_utils.py
import os
import smtplib
from email.message import EmailMessage

def send_reset_email(to_email: str, reset_link: str):
    try:
        msg = EmailMessage()
        msg["Subject"] = "Cricket Stats Pack: Password Reset"
        msg["From"] = os.getenv("EMAIL_USER")
        msg["To"] = to_email
        msg.set_content(f"""
        Hello,

        You requested to reset your password. Click the link below to proceed:
        {reset_link}

        If you didn’t request this, ignore this email.

        Regards,
        Cricket Stats Pack Team
        """)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
            smtp.send_message(msg)

        print(f"📧 Reset email sent to {to_email}")

    except Exception as e:
        print(f"❌ Failed to send reset email: {e}")
