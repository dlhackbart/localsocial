"""
Local Social notification sender.

Sends the Daily Social Plan via SMS (short nudge) + email (full plan).

Usage:
    python notify.py morning     # 8 AM Social Plan
    python notify.py gotime      # 4 PM go-time reminder
    python notify.py log         # 9:30 PM logging prompt
    python notify.py --dry-run morning   # Preview without sending
"""

import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Add scripts/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from notify_config import (
    EMAIL_FROM, EMAIL_TO, SMS_TO,
    SMTP_PASSWORD, SMTP_PORT, SMTP_SERVER, SMTP_USER,
)
from daily_social_plan import format_full_plan, format_log_prompt, format_sms, generate_plan


def send_sms(message: str, dry_run: bool = False) -> bool:
    """Send SMS via Verizon email-to-SMS gateway."""
    if dry_run:
        print(f"[SMS DRY-RUN] To: {SMS_TO}")
        print(f"[SMS DRY-RUN] Body: {message}")
        return True

    try:
        msg = MIMEText(message[:160])
        msg["From"] = EMAIL_FROM
        msg["To"] = SMS_TO
        # No subject for SMS — it just shows the body

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"[SMS SENT] {message[:80]}...")
        return True
    except Exception as e:
        print(f"[SMS FAILED] {e}")
        return False


def send_email(subject: str, body: str, dry_run: bool = False) -> bool:
    """Send full email with the Social Plan."""
    if dry_run:
        print(f"[EMAIL DRY-RUN] To: {EMAIL_TO}")
        print(f"[EMAIL DRY-RUN] Subject: {subject}")
        print(f"[EMAIL DRY-RUN] Body:\n{body}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        msg["Subject"] = subject

        # Plain text version
        msg.attach(MIMEText(body, "plain"))

        # Simple HTML version (preserves line breaks)
        html_body = body.replace("\n", "<br>\n")
        html = f"""<html><body style="font-family: -apple-system, system-ui, sans-serif;
                    color: #f4f6fa; background-color: #0e1116; padding: 20px;
                    line-height: 1.6;">
        <div style="max-width: 500px; margin: 0 auto; background-color: #171c24;
                    padding: 24px; border-radius: 16px; border: 1px solid #2a313d;">
        {html_body}
        </div>
        </body></html>"""
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"[EMAIL SENT] {subject}")
        return True
    except Exception as e:
        print(f"[EMAIL FAILED] {e}")
        return False


def morning(dry_run: bool = False):
    """8 AM — Morning Social Plan."""
    plan = generate_plan()
    full_text = format_full_plan(plan)
    sms_text = format_sms(plan)

    subject = f"Tonight: {plan['day_name']} Social Plan — {plan['call']}"
    if not plan["has_events"]:
        subject = f"Tonight: {plan['day_name']} — No events today"

    send_sms(sms_text, dry_run=dry_run)
    send_email(subject, full_text, dry_run=dry_run)


def gotime(dry_run: bool = False):
    """4 PM — Go-time reminder."""
    plan = generate_plan()
    full_text = format_full_plan(plan)
    sms_text = format_sms(plan)

    if not plan["has_events"]:
        # Still send a short "nothing tonight" nudge
        send_sms(f"{plan['day_name']}: No events tonight. Stay in.", dry_run=dry_run)
        return

    # Add urgency prefix for go-time
    sms_text = f"GO TIME — {sms_text}"
    if len(sms_text) > 160:
        sms_text = sms_text[:160]

    subject = f"Go Time: {plan['day_name']} — {plan['call']}, Grade {plan['crowd_grade']}"

    send_sms(sms_text, dry_run=dry_run)
    send_email(subject, full_text, dry_run=dry_run)


def log_prompt(dry_run: bool = False):
    """9:30 PM — Nightly logging prompt."""
    sms_text = format_log_prompt()
    send_sms(sms_text, dry_run=dry_run)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv

    if not args:
        print("Usage: python notify.py [--dry-run] <morning|gotime|log>")
        sys.exit(1)

    action = args[0].lower()

    if action == "morning":
        morning(dry_run=dry_run)
    elif action == "gotime":
        gotime(dry_run=dry_run)
    elif action == "log":
        log_prompt(dry_run=dry_run)
    else:
        print(f"Unknown action: {action}")
        print("Valid actions: morning, gotime, log")
        sys.exit(1)


if __name__ == "__main__":
    main()
