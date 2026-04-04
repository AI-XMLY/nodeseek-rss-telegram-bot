from __future__ import annotations

CATEGORY_LABELS: dict[str, str] = {
    "daily": "日常",
    "tech": "技术",
    "info": "情报",
    "review": "测评",
    "trade": "交易",
    "carpool": "拼车",
    "promo": "推广",
    "life": "生活",
    "dev": "Dev",
    "photo-share": "贴图",
    "expose": "曝光",
    "inner": "内版",
    "sandbox": "沙盒",
}

CATEGORY_ALIASES: dict[str, str] = {
    "日常": "daily",
    "技术": "tech",
    "情报": "info",
    "测评": "review",
    "交易": "trade",
    "拼车": "carpool",
    "推广": "promo",
    "promotion": "promo",
    "生活": "life",
    "dev": "dev",
    "贴图": "photo-share",
    "曝光": "expose",
    "内版": "inner",
    "沙盒": "sandbox",
}

CATEGORY_ORDER: tuple[str, ...] = (
    "daily",
    "tech",
    "info",
    "review",
    "trade",
    "carpool",
    "promo",
    "life",
    "dev",
    "photo-share",
    "expose",
    "inner",
    "sandbox",
)


def normalize_category_slug(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    if cleaned in CATEGORY_LABELS:
        return cleaned
    return CATEGORY_ALIASES.get(value.strip()) or CATEGORY_ALIASES.get(cleaned)


def category_label(slug: str | None) -> str:
    if not slug:
        return "未分类"
    return CATEGORY_LABELS.get(slug, slug)
