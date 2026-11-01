"""Email an edition's PDF over SMTP (e.g. to an HP ePrint address).

Credentials come from the environment, never from config or the repo:
  SMTP_USER       sending address, e.g. you@gmail.com
  SMTP_PASSWORD   an app password (Gmail: myaccount.google.com/apppasswords)
  SMTP_HOST/PORT  optional, default smtp.gmail.com:587
  SMTP_FROM       optional sender address when it differs from the login,
                  e.g. with Brevo (smtp-relay.brevo.com) or other relays
On macOS, SMTP_PASSWORD may instead live in the Keychain:
  security add-generic-password -s daily-brief-smtp -a you@gmail.com -w
"""

import os
import smtplib
import subprocess
import sys
from email.message import EmailMessage
from pathlib import Path

KEYCHAIN_SERVICE = "daily-brief-smtp"


def _password(user: str) -> str:
    if pw := os.environ.get("SMTP_PASSWORD"):
        return pw
    if sys.platform == "darwin":
        r = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", user, "-w"],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    sys.exit("no SMTP password: set SMTP_PASSWORD (or add it to the Keychain, see deliver.py)")


def build_message(pdf: Path, sender: str, to: list[str], subject: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = sender, ", ".join(to), subject
    msg.set_content(subject)
    msg.add_attachment(pdf.read_bytes(), maintype="application", subtype="pdf", filename=pdf.name)
    return msg


def send(pdf: Path, to: list[str], subject: str, dry_run: bool = False) -> str:
    if not to:
        sys.exit("delivery.email_to is empty in config.yaml")
    user = os.environ.get("SMTP_USER") or sys.exit("SMTP_USER is not set")
    sender = os.environ.get("SMTP_FROM", user)
    msg = build_message(pdf, sender, to, subject)
    if dry_run:
        return f"dry run: {len(msg.as_bytes()) // 1024} KB message from {sender} to {', '.join(to)}"
    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls()
        s.login(user, _password(user))
        s.send_message(msg)
    return f"sent {pdf.name} to {', '.join(to)}"
