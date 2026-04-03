# NodeSeek RSS Telegram Bot

A lightweight `RSS -> keyword filter -> Telegram push` bot for [NodeSeek RSS](https://rss.nodeseek.com/).

Supports multi-user self-service subscriptions in Telegram, multiple feeds per user, keyword matching with `any/all`, HTML rich message templates, SQLite persistence, and Docker deployment.

## Quick Start

```bash
cp .env.example .env
docker compose up -d --build
```

Set `BOT_TOKEN` in `.env`, then talk to your bot in Telegram:

```text
/start
/add https://rss.nodeseek.com/ | affman,oracle,免费鸡 | any
/list
```

## Commands

- `/add <rss_url> | <关键词1,关键词2> | <any/all> | <目标chat_id>`
- `/list`
- `/pause <订阅ID>`
- `/resume <订阅ID>`
- `/del <订阅ID>`
- `/chatid`

## Notes

- Each Telegram user manages their own feeds and keywords.
- First poll skips old items by default to avoid flooding.
- Recommended deployment: `GitHub for source + VPS for runtime`.

