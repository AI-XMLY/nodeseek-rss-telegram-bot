# NodeSeek Keyword Monitor Bot

Monitor NodeSeek keywords and push matched new posts to Telegram. Supports multi-user shared deployment, keyword toggles, multi-category filtering, delivery history, and deduplicated notifications.

## Features

- Per-keyword add / enable / disable / delete
- Multi-select category filtering
- Multiple delivery targets per user, up to 10 targets
- Delivery history
- Deduplicated notifications with persisted state
- Multi-user shared deployment

## Commands

- `/keywords`: show your keywords
- `/keywords <kw1,kw2>`: add one or more keywords
- `/on <keyword_id>`: enable a keyword
- `/off <keyword_id>`: disable a keyword
- `/delkw <keyword_id>`: delete a keyword
- `/scope`: choose categories
- `/targets`: show delivery targets
- `/addtarget`: add the current chat as a target
- `/deltarget <target_id>`: remove a target
- `/history`: show recent matched posts
- `/status`: show current settings
- `/pause`: pause notifications
- `/resume`: resume notifications
- `/chatid`: show the current chat ID

## Privacy

- This project stores Telegram user IDs, chat IDs, keywords, category settings, delivery targets, and delivery history only for notifications.
- Data is stored in the deployer's own SQLite database and is not uploaded to GitHub.
- Do not expose `.env` or the `data/` directory. If your `BOT_TOKEN` leaks, reset it in BotFather immediately.
