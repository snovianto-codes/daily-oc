import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SPIKE_THRESHOLD  = 2.0   # Alert if crypto moves +/- 2%
URGENT_THRESHOLD = 5.0   # Urgent alert if moves +/- 5%

PRICE_FILE = os.path.join(os.path.dirname(__file__), ".crypto_last_price.json")

# --- API ---
# Binance public API — free, no key, no signup, real-time live prices
BINANCE_URL = "https://api.binance.com/api/v3/ticker/price"
FOREX_URL   = "https://api.exchangerate-api.com/v4/latest/USD"
TG_URL      = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

COINS = {
    "bitcoin":  {"symbol": "BTC", "emoji": "₿", "pair": "BTCUSDT"},
    "ethereum": {"symbol": "ETH", "emoji": "Ξ", "pair": "ETHUSDT"},
}


# ─────────────────────────────────────────
# FETCH PRICES
# ─────────────────────────────────────────

def fetch_crypto_prices():
    """Fetch BTC and ETH live prices from Binance (no API key needed)."""
    prices = {}
    for coin_id, meta in COINS.items():
        try:
            res = requests.get(BINANCE_URL, params={"symbol": meta["pair"]}, timeout=10)
            res.raise_for_status()
            price = float(res.json().get("price", 0))
            if price:
                prices[coin_id] = price
        except Exception as e:
            print(f"[Binance error - {coin_id}] {e}")
    return prices


def fetch_sgd_rate():
    """Fetch USD/SGD exchange rate."""
    try:
        res = requests.get(FOREX_URL, timeout=10)
        res.raise_for_status()
        return res.json().get("rates", {}).get("SGD")
    except Exception as e:
        print(f"[Forex error] {e}")
        return None


# ─────────────────────────────────────────
# PRICE HISTORY
# ─────────────────────────────────────────

def load_last_prices():
    try:
        if os.path.exists(PRICE_FILE):
            with open(PRICE_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_last_prices(data):
    try:
        with open(PRICE_FILE, "w") as f:
            json.dump(data, f)
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

def check_crypto_alerts():
    now         = datetime.now().strftime("%d %b %Y %H:%M")
    prices      = fetch_crypto_prices()
    sgd_rate    = fetch_sgd_rate()
    last_prices = load_last_prices()

    if not prices:
        print("Could not fetch crypto prices.")
        return

    alerts         = []
    first_run_msgs = []

    for coin_id, meta in COINS.items():
        symbol    = meta["symbol"]
        emoji     = meta["emoji"]
        price     = prices.get(coin_id)

        if not price:
            continue

        price_sgd  = round(price * sgd_rate, 2) if sgd_rate else None
        last       = last_prices.get(coin_id, {})
        last_price = float(last.get("price", 0)) if last else None

        print(f"[{now}] {symbol}: ${price:,.2f} USD", end="")
        if price_sgd:
            print(f" | SGD ${price_sgd:,.2f}", end="")
        print()

        if last_price:
            change_usd = price - last_price
            change_pct = (change_usd / last_price) * 100
            abs_change = abs(change_pct)

            print(f"  Last: ${last_price:,.2f} | Change: {change_pct:+.2f}%")

            if abs_change >= URGENT_THRESHOLD:
                direction = "🚀 SURGED" if change_pct > 0 else "💥 CRASHED"
                msg = f"🚨 *URGENT CRYPTO ALERT* 🚨\n\n{emoji} *{symbol}* has {direction} {change_pct:+.2f}%\\!\n\n💰 Current: *${price:,.2f}* USD"
                if price_sgd:
                    msg += f"\n🇸🇬 SGD: *${price_sgd:,.2f}*"
                msg += f"\n📉 Previous: ${last_price:,.2f}\n📊 Change: *{change_usd:+.2f} USD \\({change_pct:+.2f}%\\)*\n🕐 {now}\n\n⚡ Consider reviewing your position\\."
                alerts.append(msg)

            elif abs_change >= SPIKE_THRESHOLD:
                direction = "📈 up" if change_pct > 0 else "📉 down"
                msg = f"⚠️ *Crypto Alert — {symbol}*\n\n{emoji} {symbol} is {direction} {change_pct:+.2f}%\n\n💰 Current: *${price:,.2f}* USD"
                if price_sgd:
                    msg += f"\n🇸🇬 SGD: *${price_sgd:,.2f}*"
                msg += f"\n📊 Change: {change_usd:+.2f} USD \\({change_pct:+.2f}%\\)\n🕐 {now}"
                alerts.append(msg)

            else:
                print(f"  No alert — {symbol} change {change_pct:+.2f}% below {SPIKE_THRESHOLD}% threshold")
        else:
            print(f"  No baseline for {symbol} — saving now.")
            line = f"{emoji} {meta['symbol']}: *${price:,.2f}* USD"
            if price_sgd:
                line += f" | SGD ${price_sgd:,.2f}"
            first_run_msgs.append(line)

        # Save current price
        last_prices[coin_id] = {
            "price":     price,
            "price_sgd": price_sgd,
            "timestamp": now
        }

    # Send alerts
    for alert in alerts:
        send_telegram(alert)

    # First run startup message
    if first_run_msgs:
        msg = "💎 *Crypto Monitor Started*\n\nBaseline prices saved:\n"
        msg += "\n".join(first_run_msgs)
        msg += f"\n\n🕐 {now}\nAlerts fire if price moves ±{SPIKE_THRESHOLD}%\\."
        send_telegram(msg)

    save_last_prices(last_prices)


# ─────────────────────────────────────────
# SNAPSHOT (for daily briefing)
# ─────────────────────────────────────────

def get_crypto_snapshot():
    """Return formatted crypto block for daily briefing."""
    prices      = fetch_crypto_prices()
    sgd_rate    = fetch_sgd_rate()
    last_prices = load_last_prices()

    if not prices:
        return "💎 *CRYPTO*\nUnavailable"

    lines = ["💎 *CRYPTO*"]
    for coin_id, meta in COINS.items():
        price = prices.get(coin_id)
        if not price:
            continue
        price_sgd  = round(price * sgd_rate, 2) if sgd_rate else None
        last       = last_prices.get(coin_id, {})
        last_price = float(last.get("price", 0)) if last else None

        line = f"{meta['emoji']} {meta['symbol']}: ${price:,.2f}"
        if price_sgd:
            line += f"  |  SGD ${price_sgd:,.2f}"
        if last_price:
            change_pct = ((price - last_price) / last_price) * 100
            arrow = "▲" if change_pct > 0 else "▼"
            line += f"  {arrow} {change_pct:+.2f}%"
        lines.append(line)

    return "\n".join(lines)


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    print(f"Checking crypto prices at {datetime.now().strftime('%H:%M')}...\n")
    check_crypto_alerts()


if __name__ == "__main__":
    main()
