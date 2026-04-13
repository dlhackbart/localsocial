# Local Social notification config
# Reuses credentials from spy_timing

import sys
from pathlib import Path

# Import SMTP/SMS config from spy_timing
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "spy_timing"))
from config import SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_TO, ALERT_SMS_TO

# Notification settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465

# SMS gateway (Verizon email-to-SMS)
SMS_GATEWAY = "vtext.com"

# Phone number (strip +1 prefix)
SMS_TO = ALERT_SMS_TO.replace("+1", "").replace("+", "") + f"@{SMS_GATEWAY}"

# Email recipient
EMAIL_TO = ALERT_EMAIL_TO
EMAIL_FROM = SMTP_USER

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
