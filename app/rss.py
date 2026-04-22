from __future__ import annotations

from dataclasses import dataclass

import aiohttp
import feedparser

from app.categories import category_label, normalize_category_slug
from app.utils import format_datetime, strip_html, truncate_text


@dataclass(slots=True)
class FeedEntry:
    item_key: str
    title: str
    link: str
    summary: str
    published_at: str
    source_text: str
    category_slug: str | None
    category_name: str


@dataclass(slots=True)
class FeedFetchResult:
    feed_title: str
    entries: list[FeedEntry]


class FeedClient:
    def __init__(self, timeout_seconds: int, max_entries_per_feed: int) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_entries_per_feed = max_entries_per_feed

    async def fetch(self, url: str) -> FeedFetchResult:
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
        headers = {"User-Agent": "NodeSeekKeywordBot/1.0 (+https://github.com/)"}
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
            plain_summary = truncate_text(strip_html(summary), 280)
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
            tag_terms = [
                strip_html(tag.get("term", ""))
                for tag in tags
                if isinstance(tag, dict) and tag.get("term")
            ]
            category_slug = None
            for term in tag_terms:
                category_slug = normalize_category_slug(term)
                if category_slug:
                    break

            source_text = " ".join(
                part for part in [title, plain_summary, " ".join(tag_terms)] if part
            ).lower()
            entries.append(
                FeedEntry(
                    item_key=item_key,
                    title=title,
                    link=link,
                    summary=plain_summary,
                    published_at=format_datetime(published_raw),
                    source_text=source_text,
                    category_slug=category_slug,
                    category_name=category_label(category_slug),
                )
            )

        return FeedFetchResult(feed_title=feed_title, entries=entries)


def match_keywords(source_text: str, keywords: list[str]) -> list[str]:
    lowered = source_text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lowered]


def _required_terms(record) -> list[str]:
    stored_terms = (
        getattr(record, "required_keywords", "")
        or getattr(record, "normalized_keyword", "")
    )
    return [term.strip().lower() for term in stored_terms.split(",") if term.strip()]


def match_keyword_rules(source_text: str, keyword_records: list) -> list:
    lowered = source_text.lower()
    matched = []
    for record in keyword_records:
        terms = _required_terms(record)
        if terms and all(term in lowered for term in terms):
            matched.append(record)
    return matched
