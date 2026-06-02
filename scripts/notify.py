"""
Local Social notification sender.

Live-music reminder (current product) + legacy Social Plan sends.

Usage:
    python notify.py weekly      # Mon refresh — re-scrape the week into weekly_music.json
    python notify.py reminder    # Daily ~4 PM — email + SMS this week's live music
    python notify.py --dry-run reminder  # Preview the email + SMS without sending

    # Legacy (no longer scheduled):
    python notify.py morning     # 8 AM Social Plan
    python notify.py gotime      # 4 PM go-time reminder
    python notify.py log         # 9:30 PM logging prompt
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
from daily_social_plan import (
    format_full_plan, format_log_prompt, format_sms, format_weekly_plan,
    generate_plan, generate_weekly_plan,
)
from weekly_music import build_weekly_music, load_weekly_music
from format_music_email import format_music_email, format_music_sms


def send_sms(message: str, dry_run: bool = False) -> bool:
    """Send MMS via Verizon email-to-MMS gateway (vzwpix.com).

    No length cap — the gateway fragments long bodies into numbered parts
    on delivery. Caller passes the full plan text.
    """
    if dry_run:
        print(f"[SMS DRY-RUN] To: {SMS_TO}")
        print(f"[SMS DRY-RUN] Body ({len(message)} chars):\n{message}")
        return True

    try:
        msg = MIMEText(message)
        msg["From"] = EMAIL_FROM
        msg["To"] = SMS_TO
        # No subject for SMS — it just shows the body

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"[SMS SENT] {len(message)} chars, preview: {message[:80]}...")
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
    """8 AM — Morning Social Plan. MMS gets the full weekly plan too (no 160-char cap)."""
    plans = generate_weekly_plan()
    today_plan = plans[0]

    # MMS: tonight (rich) + full upcoming week, 5 picks/day with reasons
    sms_text = format_sms(plans)

    # Email: full 7-day plan
    weekly_text = format_weekly_plan(plans)

    subject = f"Weekly Social Plan: {today_plan['day_name']} — {today_plan['call']}"
    if not today_plan["has_events"]:
        subject = f"Weekly Social Plan: {today_plan['day_name']} — No events tonight"

    send_sms(sms_text, dry_run=dry_run)
    send_email(subject, weekly_text, dry_run=dry_run)


def gotime(dry_run: bool = False):
    """4 PM — Go-time reminder (tonight only, no week view)."""
    plan = generate_plan()
    full_text = format_full_plan(plan)
    sms_text = format_sms(plan)

    if not plan["has_events"]:
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


def weekly(dry_run: bool = False):
    """Monday refresh — re-scrape the week's live music into data/weekly_music.json.

    With --dry-run, still builds the file (it's the source of truth) but skips any send.
    """
    week = build_weekly_music(verbose=True)
    n = len(week.get("events", []))
    print(f"[WEEKLY] refreshed — {n} events for week of {week.get('week_of')}")


def reminder(dry_run: bool = False):
    """Daily late-afternoon reminder — email + SMS of THIS week's live music (cached)."""
    week = load_weekly_music()
    if week is None:
        # No cache yet — build it now so the operator still gets something accurate.
        print("[REMINDER] no weekly cache found — building it now")
        week = build_weekly_music(verbose=True)

    email_body = format_music_email(week)
    sms_body = format_music_sms(week)

    subject = "🎵 This week's live music — Del Mar to Oceanside"
    if week.get("_stale"):
        subject = f"🎵 Live music (⚠ {week.get('_age_days','?')}d old) — Del Mar to Oceanside"

    send_email(subject, email_body, dry_run=dry_run)
    send_sms(sms_body, dry_run=dry_run)


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
    elif action == "weekly":
        weekly(dry_run=dry_run)
    elif action == "reminder":
        reminder(dry_run=dry_run)
    else:
        print(f"Unknown action: {action}")
        print("Valid actions: weekly, reminder, morning, gotime, log")
        sys.exit(1)


if __name__ == "__main__":
    main()
