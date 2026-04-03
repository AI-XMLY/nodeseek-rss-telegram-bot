from __future__ import annotations

from dataclasses import dataclass

import aiohttp
import feedparser

from app.utils import format_datetime, normalize_keywords, strip_html, truncate_text


@dataclass(slots=True)
class FeedEntry:
    item_key: str
    title: str
    link: str
    summary: str
    published_at: str
    source_text: str


@dataclass(slots=True)
class FeedFetchResult:
    feed_title: str
    entries: list[FeedEntry]


class FeedClient:
    def __init__(self, timeout_seconds: int, max_summary_length: int, max_entries_per_feed: int) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_summary_length = max_summary_length
        self.max_entries_per_feed = max_entries_per_feed

    async def fetch(self, url: str) -> FeedFetchResult:
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        headers = {"User-Agent": "NodeSeekRSSBot/1.0 (+https://github.com/)"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                raw = await response.read()

        parsed = feedparser.parse(raw)
        feed_title = strip_html(parsed.feed.get("title")) or url

        entries: list[FeedEntry] = []
        for item in parsed.entries[: self.max_entries_per_feed]:
            title = strip_html(item.get("title")) or "无标题"
            link = item.get("link", "").strip()
            summary = item.get("summary") or item.get("description") or ""
            plain_summary = truncate_text(strip_html(summary), self.max_summary_length)
            published_raw = (
                item.get("published")
                or item.get("updated")
                or item.get("created")
                or item.get("pubDate")
                or ""
            )
            item_key = (
                item.get("id")
                or item.get("guid")
                or link
                or f"{title}:{published_raw}"
            )
            tags = item.get("tags") or []
            tag_text = " ".join(
                strip_html(tag.get("term", ""))
                for tag in tags
                if isinstance(tag, dict) and tag.get("term")
            )
            source_text = " ".join(
                part for part in [title, plain_summary, tag_text] if part
            ).lower()
            entries.append(
                FeedEntry(
                    item_key=item_key,
                    title=title,
                    link=link,
                    summary=plain_summary or "这条 RSS 没有摘要，可直接点开原帖查看。",
                    published_at=format_datetime(published_raw),
                    source_text=source_text,
                )
            )

        return FeedFetchResult(feed_title=feed_title, entries=entries)


def match_keywords(source_text: str, raw_keywords: str, match_mode: str) -> tuple[bool, list[str]]:
    keywords = normalize_keywords(raw_keywords)
    if not keywords:
        return True, []

    matched = [keyword for keyword in keywords if keyword in source_text]
    if match_mode == "all":
        return len(matched) == len(keywords), matched
    return len(matched) > 0, matched
