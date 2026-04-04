# Daily Briefing Skill

Sends a personalised morning briefing to Telegram every day at 7:30am SGT, and handles conversational follow-ups in the same Telegram chat.

## What this skill does

Every morning at 7:30am, run the daily briefing script. It will:

1. Fetch Singapore weather from the NEA API — 2-hour forecast and 24-hour outlook (temperature, humidity, wind, rain warning)
2. Fetch live gold price in USD and SGD, plus USD/SGD forex rate and % change since yesterday
3. Fetch live BTC and ETH prices from Binance, with % change since last check
4. Fetch top AI/tech/Singapore news via NewsAPI and summarise the 5 most relevant stories using Claude
5. Fetch the last 7 days of Gmail (unread, important, or primary) and triage them into: action needed / good to know / can ignore
6. Combine everything into one Telegram message and send it
7. Save today's briefing data to `briefing_context.json` for follow-up reference

## How to trigger

### Scheduled (automatic)
Runs daily at 7:30am SGT via OpenClaw cron job `daily-briefing` on session `daily-oc`.

### Manual trigger
If asked to send the morning briefing, run the script directly:

```bash
cd /Users/novianto/Documents/Python/OpenClaw/Daily-OC && python daily_briefing.py
```

Trigger phrases:
- "send me the daily briefing"
- "morning briefing"
- "what's the weather and news today?"

## Handling follow-up questions

After the morning briefing is sent, the user may reply in Telegram with follow-up questions. Handle these conversationally using the context saved in `briefing_context.json`.

### How to read today's context

```bash
cat /Users/novianto/Documents/Python/OpenClaw/Daily-OC/briefing_context.json
```

This file contains today's headlines, gold price, BTC/ETH prices, and forex rate. Always reference exact numbers from this file when answering market questions.

### News follow-ups

Trigger phrases:
- "tell me more about [story]"
- "what's the MAS story about?"
- "expand on the AI news"
- "why is [topic] important?"

How to respond:
- Read `briefing_context.json` to recall today's headlines
- Use your own knowledge to expand on the story
- If you need fresher details, use web search
- Keep responses concise — 3 to 5 sentences unless the user asks for more
- Always connect the story back to why it matters for Singapore or AI/tech

### Market follow-ups

Trigger phrases:
- "what's driving gold today?"
- "why is BTC up/down?"
- "should I be worried about the price move?"
- "what does this mean for markets?"

How to respond:
- Read `briefing_context.json` for today's exact prices and % changes
- Give a brief macro context (e.g. USD strength, risk-off sentiment, Fed news)
- Use web search if the move is significant and you need current context
- Do not give financial advice — frame as context and information only
- Keep it to 3 to 5 sentences

### General follow-ups

If the user asks anything else related to the briefing (weather, emails, etc.), use the context in `briefing_context.json` and answer naturally. If the question is unrelated to the briefing, handle it as a normal conversation.

## Session

This skill runs on session `daily-oc` (persistent). The session retains context from the morning briefing run, so follow-ups within the same day will have access to what was sent.

## Script location

```
/Users/novianto/Documents/Python/OpenClaw/Daily-OC/daily_briefing.py
```

## Context file

```
/Users/novianto/Documents/Python/OpenClaw/Daily-OC/briefing_context.json
```

Saved after every briefing run. Contains:
- `date` — briefing date and time
- `headlines` — list of today's top 5 news headlines with sources
- `gold_usd` — gold price in USD
- `gold_sgd` — gold price in SGD
- `usd_sgd` — forex rate
- `gold_change_pct` — % change since yesterday
- `btc_usd` — BTC price in USD
- `eth_usd` — ETH price in USD
- `btc_change_pct` — BTC % change
- `eth_change_pct` — ETH % change

## Environment

Requires `.env` at:
```
/Users/novianto/Documents/Python/OpenClaw/Daily-OC/.env
```

Keys needed:
- `ANTHROPIC_API_KEY` — Claude Haiku for news and email summarisation
- `NEWS_API_KEY` — NewsAPI for headlines
- `TELEGRAM_TOKEN` — Telegram bot token
- `TELEGRAM_CHAT_ID` — Your Telegram chat ID
- `AREA` — defaults to Singapore

Gmail auth uses `token.pickle` in the same folder. If it's missing or expired, re-run the OAuth flow.

## Gold alert (separate job)

`gold_alert.py` runs separately every 30 minutes to monitor intraday gold price spikes.
- Alerts at ±2% change
- Urgent alert at ±5% change
- Baseline price saved to `.gold_last_price.json`

## Crypto alert (separate job)

`crypto_alert.py` runs separately every 30 minutes to monitor BTC and ETH price spikes.
- Alerts at ±2% change
- Urgent alert at ±5% change
- Baseline prices saved to `.crypto_last_price.json`
- Uses Binance public API (no key needed)
