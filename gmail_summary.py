import os
import pickle
import base64
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

# --- CONFIG ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID  = os.getenv("TELEGRAM_CHAT_ID")

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_URL   = "https://api.anthropic.com/v1/messages"
TG_URL       = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

TOKEN_FILE       = os.path.join(os.path.dirname(__file__), "token.pickle")
MAX_EMAILS       = 15  # Max emails to fetch
MAX_BODY_CHARS   = 300 # Max chars per email body to send to Claude


# ─────────────────────────────────────────
# GMAIL AUTH
# ─────────────────────────────────────────

def get_gmail_service():
    """Load saved credentials and return Gmail service."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    # Refresh token if expired
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    if not creds:
        print("❌ No token found. Run authentication script first.")
        return None

    return build("gmail", "v1", credentials=creds)


# ─────────────────────────────────────────
# FETCH EMAILS
# ─────────────────────────────────────────

def clean_text(text):
    """Remove HTML tags and extra whitespace."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_email_body(payload):
    """Extract plain text body from email payload."""
    body = ""
    if payload.get("body", {}).get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    elif payload.get("parts"):
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                break
            elif part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
    return clean_text(body)[:MAX_BODY_CHARS]


def fetch_recent_emails(service):
    """Fetch unread emails from last 24 hours."""
    try:
        # Query: unread emails from last 24h, exclude promotions/social/spam
        query = "newer_than:7d (is:unread OR is:important OR category:primary)"

        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=MAX_EMAILS
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return []

        emails = []
        for msg in messages:
            msg_data = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="full"
            ).execute()

            headers = msg_data.get("payload", {}).get("headers", [])
            header_dict = {h["name"]: h["value"] for h in headers}

            sender  = header_dict.get("From", "Unknown")
            subject = header_dict.get("Subject", "(No subject)")
            date    = header_dict.get("Date", "")
            body    = get_email_body(msg_data.get("payload", {}))

            emails.append({
                "sender":  sender,
                "subject": subject,
                "date":    date,
                "body":    body
            })

        return emails

    except Exception as e:
        print(f"[Gmail error] {e}")
        return []


# ─────────────────────────────────────────
# SUMMARIZE WITH CLAUDE
# ─────────────────────────────────────────

def summarize_emails(emails):
    """Send emails to Claude and get action items."""
    if not emails:
        return "📭 No unread emails in the last 24 hours."

    email_text = ""
    for i, e in enumerate(emails, 1):
        email_text += f"\n---Email {i}---\nFrom: {e['sender']}\nSubject: {e['subject']}\nBody: {e['body']}\n"

    prompt = f"""You are an executive assistant reviewing emails for a busy professional in Singapore.

Here are their unread emails from the last 24 hours:
{email_text}

Analyze these emails and provide:
1. Emails that need a REPLY or ACTION (list sender, subject, what's needed)
2. Important information to be aware of
3. Emails that can be ignored or are FYI only

Format exactly like this:
🔴 ACTION NEEDED:
• [Sender name] — [Subject] — [What to do]

🟡 GOOD TO KNOW:
• [Brief note]

✅ CAN IGNORE:
• [Count] newsletters/notifications

Keep it concise. No lengthy explanations."""

    headers = {
        "x-api-key":         ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type":      "application/json"
    }
    body = {
        "model":      CLAUDE_MODEL,
        "max_tokens": 600,
        "messages":   [{"role": "user", "content": prompt}]
    }
    try:
        res = requests.post(CLAUDE_URL, headers=headers, json=body, timeout=15)
        res.raise_for_status()
        return res.json()["content"][0]["text"].strip()
    except Exception as e:
        print(f"[Claude error] {e}")
        return "Could not summarize emails."


# ─────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────

def send_telegram(message):
    try:
        payload = {
            "chat_id":    TELEGRAM_CHAT_ID,
            "text":       message,
            "parse_mode": "Markdown"
        }
        res = requests.post(TG_URL, json=payload, timeout=10)
        res.raise_for_status()
        print("✅ Gmail summary sent to Telegram!")
    except Exception as e:
        print(f"[Telegram error] {e}")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def get_gmail_block():
    """Return formatted Gmail block for daily briefing."""
    service = get_gmail_service()
    if not service:
        return "📧 *GMAIL*\nCould not connect to Gmail."

    emails  = fetch_recent_emails(service)
    summary = summarize_emails(emails)

    return f"📧 *GMAIL — {len(emails)} unread*\n{summary}"


def main():
    print(f"Fetching Gmail summary at {datetime.now().strftime('%H:%M')}...\n")

    service = get_gmail_service()
    if not service:
        return

    emails  = fetch_recent_emails(service)
    print(f"Found {len(emails)} unread emails\n")

    summary = summarize_emails(emails)
    now     = datetime.now().strftime("%A, %d %b %Y • %H:%M")

    briefing = f"""📧 *GMAIL SUMMARY*
📅 {now}
─────────────────────────────

{summary}

─────────────────────────────
_Sent by Daily\\-OC_ 🤖"""

    print(briefing)
    print()
    send_telegram(briefing)


if __name__ == "__main__":
    main()
