# NodeSeek RSS Telegram Bot

[English](./README.md) | [简体中文](./README.zh-CN.md)

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

- `/add <rss_url> | <keyword1,keyword2> | <any/all> | <target_chat_id>`
- `/list`
- `/pause <subscription_id>`
- `/resume <subscription_id>`
- `/del <subscription_id>`
- `/chatid`

## Notes

- Each Telegram user manages their own feeds and keywords.
- The first poll skips old items by default to avoid flooding.
- Recommended deployment: `GitHub for source + VPS for runtime`.

