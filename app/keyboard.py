from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.categories import CATEGORY_ORDER, category_label


def build_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("新建关键词"), KeyboardButton("我的关键词")],
            [KeyboardButton("版块设置"), KeyboardButton("推送历史")],
            [KeyboardButton("添加当前聊天"), KeyboardButton("帮助")],
        ],
        resize_keyboard=True,
    )


def build_category_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    rows = []
    for slug in CATEGORY_ORDER:
        marker = "✅" if slug in selected else "⬜️"
        rows.append(
            [
                InlineKeyboardButton(
                    f"{marker} {category_label(slug)}",
                    callback_data=f"scope:toggle:{slug}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton("监控全部", callback_data="scope:all"),
            InlineKeyboardButton("完成", callback_data="scope:done"),
        ]
    )
    return InlineKeyboardMarkup(rows)

