# NodeSeek RSS Telegram Bot

[简体中文](./README.md) | [English](./README.en.md)

A lightweight `RSS -> keyword filter -> Telegram push` bot for [NodeSeek RSS](https://rss.nodeseek.com/).

One admin deploys a shared bot, and multiple users manage their own feeds, keywords, and target chats directly in Telegram.

## Highlights

- Multi-user shared bot
- Self-service subscriptions in Telegram
- Multiple feeds per user
- `any` / `all` keyword matching
- HTML rich message templates
- SQLite persistence
- Docker deployment

## Quick Start

```bash
cp .env.example .env
```

Set `BOT_TOKEN` in `.env`, then start:

```bash
docker compose up -d --build
```

Then send these commands to your bot in Telegram:

```text
/start
/add https://rss.nodeseek.com/
/keywords 1 affman,oracle,免费鸡
/mode 1 any
/list
```

## Commands

- `/add <rss_url>`: create a new RSS subscription
- `/keywords <subscription_id> <keyword1,keyword2>`: set keywords for that subscription
- `/mode <subscription_id> <any/all>`: set keyword match mode
- `/target <subscription_id> <target_chat_id>`: change the destination chat
- `/list`: show all your subscriptions
- `/pause <subscription_id>`: pause a subscription
- `/resume <subscription_id>`: resume a subscription
- `/del <subscription_id>`: delete a subscription
- `/chatid`: show the current chat ID

## Notes

- Recommended setup: source on GitHub, one VPS for runtime, one shared bot for multiple users.
- The first poll skips old items by default to avoid flooding.
- The default limit is `20` subscriptions per user, configurable with `MAX_SUBSCRIPTIONS_PER_USER` in `.env`.

## Privacy

- This project stores Telegram user ID, chat ID, username, feed URLs, keywords, and target chats only for subscription and delivery.
- Data is stored in your own server-side SQLite database by default and is not uploaded to GitHub.
- Do not expose `.env` or the `data/` directory. If your `BOT_TOKEN` leaks, reset it in BotFather immediately.
