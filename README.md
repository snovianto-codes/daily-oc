# 🌅 Daily-OC - Personal AI Assistant

> A personal learning prototype exploring OpenClaw's agent and cron system. Daily-OC is a 24/7 AI assistant that delivers a personalised morning briefing to Telegram every day at 7:30am SGT - and stays available for conversational follow-ups throughout the day.

This is intentionally modular - new agents (e.g. a task manager, calendar briefing, or portfolio tracker) can be added as separate skills under `skills/`.

---

## What It Does

### 🌅 Morning Briefing (7:30am SGT, automatic)

Every morning, Daily-OC wakes up and sends a single Telegram message with everything you need to start the day:

- **🌤 Weather** - Real-time 2-hour and 24-hour NEA forecasts for Singapore, including temperature, humidity, wind, and rain alerts
- **💰 Gold & Markets** - Live gold price in USD and SGD, USD/SGD forex rate, and % change since yesterday
- **💎 Crypto** - Live BTC and ETH prices from Binance, with % change since last check
- **📰 Top News** - 5 curated AI/tech/Singapore headlines summarised by Claude Haiku
- **📧 Gmail Digest** - Last 7 days of important emails categorised into: action needed, good to know, and can ignore

### 💬 Conversational Follow-ups (anytime, via Telegram)

After the briefing lands, just reply in the same Telegram chat. The OpenClaw agent picks up your message and responds intelligently:

- **"Tell me more about the OpenAI funding story"** → searches the web for current data, gives a breakdown with analysis
- **"What's driving gold today?"** → pulls today's exact price from context, adds macro reasoning
- **"Why is BTC up?"** → references live prices, explains market dynamics
- **Any follow-up question** → agent uses SKILL.md instructions, today's briefing context, and web search to respond

This works because OpenClaw keeps the Telegram channel live 24/7 - the briefing is just the starting point, not the end of the conversation.

---

## Architecture

```
cron (7:30am SGT)
    └── daily_briefing.py
            ├── NEA API          → weather block
            ├── gold-api.com     → gold price block
            ├── exchangerate-api → USD/SGD rate
            ├── Binance API      → BTC & ETH live prices
            ├── NewsAPI          → headlines
            ├── Claude Haiku API → news summary + email triage
            ├── Gmail API        → email fetch
            ├── Telegram Bot API → send briefing
            └── briefing_context.json → saved for follow-up Q&A

OpenClaw (24/7)
    └── Telegram channel (polling)
            └── user replies → agent reads SKILL.md
                    ├── briefing_context.json → today's data
                    ├── web search → fresh context
                    └── Claude Haiku → conversational response → Telegram
```

**Standalone alert scripts (every 30 min):**
- `gold_alert.py` - alerts at ±2% gold price move, urgent at ±5%
- `crypto_alert.py` - alerts at ±2% BTC/ETH move, urgent at ±5%

---

## Tech Stack

| Layer | Tool |
|---|---|
| Language | Python 3 |
| AI Summarisation & Chat | Claude Haiku (Anthropic API) |
| Email | Gmail API (OAuth2) |
| Weather | NEA Data.gov.sg API (free, no key) |
| Gold Price | gold-api.com (free, no key) |
| Crypto Price | Binance Public API (free, no key, live) |
| Forex | exchangerate-api.com (free) |
| News | NewsAPI.org |
| Delivery & Conversation | Telegram Bot API |
| Agent Platform | OpenClaw |
| Scheduling | OpenClaw Cron (`0 7 * * *`, SGT) |

---

## Project Structure

```
Daily-OC/
├── daily_briefing.py           # Main script - orchestrates all blocks
├── gold_alert.py               # Standalone gold price spike monitor
├── crypto_alert.py             # Standalone BTC/ETH price spike monitor
├── gmail_summary.py            # Standalone Gmail digest (dev reference)
├── briefing_context.json       # Today's briefing data for follow-up Q&A
├── token.pickle                # Saved Gmail credentials (gitignored)
├── credentials.json            # Google OAuth client config (gitignored)
├── .gold_last_price.json       # Persisted gold baseline price
├── .crypto_last_price.json     # Persisted crypto baseline prices
├── .env                        # Secret keys (gitignored)
├── .env.example                # Template for .env
├── briefing.log                # stdout log
├── briefing_error.log          # stderr log
└── skills/
    └── daily-briefing/
        ├── SKILL.md            # OpenClaw agent behaviour + follow-up instructions
        └── cron.json           # Cron job reference
```

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/snovianto-codes/openclaw-daily-oc.git
cd openclaw-daily-oc
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

```env
ANTHROPIC_API_KEY=your_key_here
NEWS_API_KEY=your_key_here
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
AREA=Singapore
NEWS_KEYWORDS=AI agents OR Singapore tech OR Southeast Asia startup OR MAS fintech
```

### 3. Authenticate Gmail

Download `credentials.json` from Google Cloud Console (Gmail API, Desktop app), then run:

```bash
python auth_gmail.py
```

### 4. Set up OpenClaw

Install and configure OpenClaw, then add cron jobs:

```bash
# Daily morning briefing
openclaw cron add \
  --name "daily-briefing" \
  --cron "0 7 * * *" \
  --tz "Asia/Singapore" \
  --session isolated \
  --message "python /path/to/Daily-OC/daily_briefing.py"

# Gold price monitor (every 30 min)
openclaw cron add \
  --name "gold-alert" \
  --cron "*/30 * * * *" \
  --tz "Asia/Singapore" \
  --session isolated \
  --message "python /path/to/Daily-OC/gold_alert.py"

# Crypto price monitor (every 30 min)
openclaw cron add \
  --name "crypto-alert" \
  --cron "*/30 * * * *" \
  --tz "Asia/Singapore" \
  --session isolated \
  --message "python /path/to/Daily-OC/crypto_alert.py"
```

### 5. Pair Telegram

Start a conversation with your bot in Telegram. OpenClaw will send a pairing code - approve it with:

```bash
openclaw pairing approve telegram <code>
```

Once paired, the agent listens to your Telegram chat 24/7 and responds to follow-up messages automatically.

---

## Sample Output

**Morning briefing (automatic):**
```
🌅 DAILY BRIEFING
📅 Saturday, 04 Apr 2026 • 07:30
──────────────────────────────

🌤 WEATHER - Singapore
🕐 Right now: Partly Cloudy  ☀️ No rain expected
🌡 25°C – 33°C  💧70–90%

💰 GOLD & MARKETS
🥇 Gold: $4,678.00/oz  |  SGD $6,034.62/oz
💱 USD/SGD: 1.3400
📊 Since yesterday: ▲ +0.82%

💎 CRYPTO
₿ BTC: $83,245.12  |  SGD $111,548.46  ▲ +1.24%
Ξ ETH: $1,842.30   |  SGD $2,468.68   ▼ -0.53%

📰 TOP NEWS
1. [TechCrunch] US VC funding hits record $267B in Q1 2026...
2. [CNA] MAS expands fintech sandbox to cover AI agents...

📧 GMAIL - 8 emails
🔴 ACTION NEEDED:
• Google - Security alert - Review account activity immediately
✅ CAN IGNORE:
• 3 newsletters/notifications
```

**Conversational follow-up (anytime):**
```
You: tell me more about the VC funding story

Agent: Let me search for more details on this...

Record $267B in US VC funding for Q1 2026 - literally
doubled the previous quarterly record.

• OpenAI: $122B (45% of total)
• Anthropic: $30B
• xAI: $20B

→ These 3 deals alone = 63% of all venture funding that quarter.

For you: This is worth watching if you care about AI strategy.
Capital concentration this extreme means most of the frontier
AI progress will come from just a handful of labs...
```

---

## How the Conversational Follow-up Works

1. `daily_briefing.py` saves `briefing_context.json` after every run with today's exact prices and headlines
2. OpenClaw keeps the Telegram channel open 24/7 via polling
3. When you reply, the agent reads `SKILL.md` to understand how to respond
4. It loads `briefing_context.json` for today's data, uses web search for fresher context, and Claude Haiku for reasoning
5. Response lands in the same Telegram chat within seconds

---

## Part of the OpenClaw Portfolio

Daily-OC is one project in the **OpenClaw** series - a personal portfolio of AI-powered tools built at the intersection of business strategy and practical automation.

Other projects: [GitHub/snovianto-codes](https://github.com/snovianto-codes)
