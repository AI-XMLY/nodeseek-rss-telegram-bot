from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from app.bot import build_application
from app.config import Settings
from app.db import Database
from app.poller import FeedPoller


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    # Telegram requests include the bot token in the URL, so keep HTTP client logs quiet.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


async def serve() -> None:
    settings = Settings.load()
    configure_logging(settings.log_level)

    db = Database(settings.database_path)
    await db.init()

    poller = FeedPoller(settings, db)
    application = build_application(settings, db)
    await application.initialize()
    await application.start()
    poller_task = asyncio.create_task(poller.run_forever(application.bot))
    await application.updater.start_polling()

    try:
        await asyncio.Future()
    finally:
        await poller.stop()
        poller_task.cancel()
        with suppress(asyncio.CancelledError):
            await poller_task
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
