import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Alert thresholds
SPIKE_THRESHOLD  = 2.0   # Alert if gold moves +/- 2%
URGENT_THRESHOLD = 5.0   # Urgent alert if moves +/- 5%

# File to store last known price
PRICE_FILE = os.path.join(os.path.dirname(__file__), ".gold_last_price.json")

# --- API ENDPOINTS (all free, no key needed) ---
GOLD_URL = "https://api.gold-api.com/price/XAU"
FOREX_URL = "https://api.exchangerate-api.com/v4/latest/USD"
TG_URL   = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"


# ─────────────────────────────────────────
# FETCH PRICES
# ─────────────────────────────────────────

def fetch_gold_price():
    """Fetch current gold price in USD per oz — no API key needed."""
    try:
        res = requests.get(GOLD_URL, timeout=10)
        res.raise_for_status()
        data = res.json()
        return {
            "price":     data.get("price"),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"[Gold API error] {e}")
        return None


def fetch_sgd_rate():
    """Fetch USD/SGD exchange rate — no key needed."""
    try:
        res = requests.get(FOREX_URL, timeout=10)
        res.raise_for_status()
        rates = res.json().get("rates", {})
        return rates.get("SGD")
    except Exception as e:
        print(f"[Forex error] {e}")
        return None


# ─────────────────────────────────────────
# PRICE HISTORY (local file)
# ─────────────────────────────────────────

def load_last_price():
    """Load last saved gold price from file."""
    try:
        if os.path.exists(PRICE_FILE):
            with open(PRICE_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def save_last_price(price_data):
    """Save current gold price to file."""
    try:
        with open(PRICE_FILE, "w") as f:
            json.dump(price_data, f)
    except Exception as e:
        print(f"[Save error] {e}")


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
        print("✅ Alert sent to Telegram!")
    except Exception as e:
        print(f"[Telegram error] {e}")


# ─────────────────────────────────────────
# ALERT LOGIC
# ─────────────────────────────────────────

def check_gold_alert():
    now = datetime.now().strftime("%d %b %Y %H:%M")

    # Fetch current price
    gold = fetch_gold_price()
    if not gold or not gold.get("price"):
        print("Could not fetch gold price.")
        return

    current_price = float(gold["price"])
    sgd_rate      = fetch_sgd_rate()
    price_sgd     = round(current_price * sgd_rate, 2) if sgd_rate else None

    print(f"[{now}] Gold: ${current_price:,.2f}/oz USD", end="")
    if price_sgd:
        print(f" | SGD ${price_sgd:,.2f}/oz", end="")
    print()

    # Load last price for comparison
    last = load_last_price()

    if last and last.get("price"):
        last_price = float(last["price"])
        change_usd = current_price - last_price
        change_pct = (change_usd / last_price) * 100
        abs_change = abs(change_pct)

        print(f"Last price: ${last_price:,.2f} | Change: {change_pct:+.2f}%")

        if abs_change >= URGENT_THRESHOLD:
            direction = "🚀 SURGED" if change_pct > 0 else "💥 CRASHED"
            message = f"""🚨 *URGENT GOLD ALERT* 🚨

Gold has {direction} {change_pct:+.2f}%\\!

💰 Current: *${current_price:,.2f}/oz* USD"""
            if price_sgd:
                message += f"\n🇸🇬 SGD: *${price_sgd:,.2f}/oz*"
            message += f"""
📉 Previous: ${last_price:,.2f}/oz
📊 Change: *{change_usd:+.2f} USD \\({change_pct:+.2f}%\\)*
🕐 {now}

⚡ Consider reviewing your position\\."""
            send_telegram(message)

        elif abs_change >= SPIKE_THRESHOLD:
            direction = "📈 up" if change_pct > 0 else "📉 down"
            message = f"""⚠️ *Gold Price Alert*

Gold is {direction} {change_pct:+.2f}%

💰 Current: *${current_price:,.2f}/oz* USD"""
            if price_sgd:
                message += f"\n🇸🇬 SGD: *${price_sgd:,.2f}/oz*"
            message += f"\n📊 Change: {change_usd:+.2f} USD \\({change_pct:+.2f}%\\)\n🕐 {now}"
            send_telegram(message)

        else:
            print(f"No alert needed — change {change_pct:+.2f}% below {SPIKE_THRESHOLD}% threshold")

    else:
        print("No previous price found — saving baseline price.")
        send_telegram(f"""💰 *Gold Monitor Started*

Baseline price saved\\:
🥇 Gold: *${current_price:,.2f}/oz* USD""" + (f"\n🇸🇬 SGD: *${price_sgd:,.2f}/oz*" if price_sgd else "") + f"\n🕐 {now}\n\nAlerts will fire if price moves ±{SPIKE_THRESHOLD}%\\.")

    # Always save current price
    save_last_price({
        "price":     current_price,
        "price_sgd": price_sgd,
        "timestamp": now
    })


def get_gold_snapshot():
    """Return formatted gold block for daily briefing."""
    gold = fetch_gold_price()
    sgd  = fetch_sgd_rate()

    if not gold or not gold.get("price"):
        return "💰 Gold: Unavailable"

    price     = float(gold["price"])
    price_sgd = round(price * sgd, 2) if sgd else None
    last      = load_last_price()

    lines = ["💰 *GOLD & MARKETS*"]
    if price_sgd:
        lines.append(f"🥇 Gold: ${price:,.2f}/oz  |  SGD ${price_sgd:,.2f}/oz")
    else:
        lines.append(f"🥇 Gold: ${price:,.2f}/oz USD")
    if sgd:
        lines.append(f"💱 USD/SGD: {sgd:.4f}")
    if last and last.get("price"):
        last_price = float(last["price"])
        change_pct = ((price - last_price) / last_price) * 100
        arrow = "▲" if change_pct > 0 else "▼"
        lines.append(f"📊 Change: {arrow} {change_pct:+.2f}%")

    return "\n".join(lines)


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    print(f"Checking gold price at {datetime.now().strftime('%H:%M')}...\n")
    check_gold_alert()


if __name__ == "__main__":
    main()
