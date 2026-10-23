import os
from backend.utils.email_service import send_email

recipient = os.getenv("SMTP_FROM_EMAIL")

if not recipient:
    raise RuntimeError("SMTP_FROM_EMAIL is missing from .env")

try:
    send_email(
        recipient=recipient,
        subject="Cricbuzz LiveStats - Email Test",
        body=(
            "Hello!\n\n"
            "This is a test email from Cricbuzz LiveStats.\n"
            "Your email service is working if you received this message.\n\n"
            "Cricbuzz LiveStats Team"
        ),
    )
    print("SUCCESS: Test email sent.")
except Exception:
    print("FAILED: Email could not be sent. Check your SMTP settings and credentials.")
    raise
