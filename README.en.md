# NodeSeek Keyword Monitor Bot

Monitor NodeSeek keywords and push matched new posts to Telegram. Supports multi-user shared deployment, keyword combinations, block keywords, multi-category filtering, delivery history, and deduplicated notifications.

## Features

- Per-keyword add / enable / disable / delete
- Keyword combinations, for example `dmit + corona` only matches when all terms appear
- Block keywords, so matched blocked terms suppress notifications
- Multi-select category filtering
- Multiple delivery targets, up to 10 in total across user chats and communities
- Delivery history
- Deduplicated notifications with persisted state
- Multi-user shared deployment
- Polls RSS every 10 seconds by default, configurable in `.env`

Common commands:

- `/keywords`: show your keywords
- `/keywords <kw1,kw2>`: add one or more keywords
- `/combo <kw1,kw2>`: add a keyword combination that requires all terms
- `/on <keyword_id>`: enable a keyword
- `/off <keyword_id>`: disable a keyword
- `/delkw <keyword_id>`: delete a keyword
- `/block <kw1,kw2>`: add block keywords
- `/blocks`: show block keywords
- `/delblock <block_keyword_id>`: delete a block keyword
- `/addtarget`: add the current chat as a target
- `/addtarget <chat_id>`: bind a group or channel from private chat
- `/targets`: show delivery targets
- `/deltarget <target_id>`: remove a target
- `/history`: show recent matched posts
- `/status`: show current settings
- `/pause`: pause notifications
- `/resume`: resume notifications

Notes:

- Private chats work by default, and you do not need to run `/addtarget` manually
- In groups, you can run `/addtarget` directly
- For channels, use `/addtarget <chat_id>` in private chat
- The operator must be an admin of the target group or channel
- If `ALLOWED_USER_IDS` is enabled, only allowlisted users can use the bot

## Try My Bot First

[https://t.me/NodeSeekKey_bot](https://t.me/NodeSeekKey_bot)

## Personal Deployment Guide

### 1. Prepare Your VPS

Install Docker and Git on your VPS:

```bash
apt update
apt install -y docker.io docker-compose-plugin git
```

### 2. Create a Telegram Bot

Open Telegram, talk to `@BotFather`, create a new bot, and keep the `BOT_TOKEN` it gives you.

### 3. Clone the Project

Run this on your VPS:

```bash
git clone https://github.com/<your-username>/nodeseek-rss-telegram-bot.git
cd nodeseek-rss-telegram-bot
```

### 4. Configure Environment Variables

Copy the config template:

```bash
cp .env.example .env
nano .env
```

Replace `BOT_TOKEN` in `.env` with your own token.

If you want allowlist mode, you can also add:

```text
ALLOWED_USER_IDS=<user_id_1>,<user_id_2>
```

### 5. Start the Bot

```bash
docker compose up -d --build
```

### 6. Check Logs

```bash
docker compose logs -f
```

If you see `Application started`, the bot is running.

Press `Ctrl + C` to exit log viewing. This will not stop the bot.

### 7. Update the Project

For normal updates, run:

```bash
git pull
docker compose down
docker compose up -d --build
```

If your VPS reports a Git branch conflict, force it to match GitHub:

```bash
git fetch origin
git reset --hard origin/main
docker compose down
docker compose up -d --build
```

## Privacy

- This project stores Telegram user IDs, chat IDs, keywords, category settings, delivery targets, and delivery history only for notifications.
- Data is stored in the deployer's own SQLite database and is not uploaded to GitHub.
- Do not expose `.env` or the `data/` directory. If your `BOT_TOKEN` leaks, reset it in BotFather immediately.
