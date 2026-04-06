# NodeSeek Keyword Monitor Bot

Monitor NodeSeek keywords and push matched new posts to Telegram. Supports multi-user shared deployment, keyword toggles, multi-category filtering, delivery history, and deduplicated notifications.

## Features

- Per-keyword add / enable / disable / delete
- Multi-select category filtering
- Multiple delivery targets per user, up to 10 targets
- Delivery history
- Deduplicated notifications with persisted state
- Multi-user shared deployment

## User Beginner Guide

If you only want to use the bot, you do not need to know VPS or Docker.

1. Open the bot in Telegram and send:

```text
/start
```

2. Add the keywords you want to monitor:

```text
/keywords oracle,免费鸡,甲骨文
```

3. If you only want some categories, send:

```text
/scope
```

Then choose categories with the buttons.

4. Check your current settings:

```text
/status
```

5. Check recent matched posts:

```text
/history
```

Common commands:

- `/keywords`: show your keywords
- `/keywords <kw1,kw2>`: add one or more keywords
- `/on <keyword_id>`: enable a keyword
- `/off <keyword_id>`: disable a keyword
- `/delkw <keyword_id>`: delete a keyword
- `/addtarget`: add the current chat as a target
- `/targets`: show delivery targets
- `/deltarget <target_id>`: remove a target
- `/history`: show recent matched posts
- `/status`: show current settings
- `/pause`: pause notifications
- `/resume`: resume notifications

## Developer Beginner Guide

If you want to deploy your own bot for yourself or others, just follow these steps.

1. Prepare a VPS and install Docker and Git:

```bash
apt update
apt install -y docker.io docker-compose-plugin git
```

2. Create a bot with `@BotFather` on Telegram and get your `BOT_TOKEN`

3. Clone the project on your VPS:

```bash
git clone https://github.com/<your-username>/nodeseek-rss-telegram-bot.git
cd nodeseek-rss-telegram-bot
```

4. Create the config file:

```bash
cp .env.example .env
nano .env
```

Replace `BOT_TOKEN` with your own token.

5. Start the bot:

```bash
docker compose up -d --build
```

6. Check whether it started successfully:

```bash
docker compose logs -f
```

If you see `Application started`, the bot is running.

7. Update the project later with:

```bash
git pull
docker compose down
docker compose up -d --build
```

## Privacy

- This project stores Telegram user IDs, chat IDs, keywords, category settings, delivery targets, and delivery history only for notifications.
- Data is stored in the deployer's own SQLite database and is not uploaded to GitHub.
- Do not expose `.env` or the `data/` directory. If your `BOT_TOKEN` leaks, reset it in BotFather immediately.
