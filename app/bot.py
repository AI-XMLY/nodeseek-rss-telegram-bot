from __future__ import annotations

from dataclasses import dataclass

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.categories import CATEGORY_ORDER, category_label, normalize_category_slug
from app.config import Settings
from app.db import Database, UserRecord
from app.keyboard import build_category_keyboard, build_main_menu

MAIN_MENU_TEXT = (
    "欢迎使用 NodeSeek 关键词监控 Bot。\n\n"
    "你可以添加关键词、筛选版块、设置多个推送目标，并通过 /history 回看命中记录。"
)

HELP_TEXT = """
可用命令：
/start - 打开主菜单
/help - 查看帮助
/keywords - 查看我的关键词
/keywords <关键词1,关键词2> - 一次添加一个或多个关键词
/addkw <关键词> - 添加单个关键词
/on <关键词ID> - 开启一个关键词
/off <关键词ID> - 关闭一个关键词
/delkw <关键词ID> - 删除一个关键词
/scope - 通过按钮选择监控版块（支持多选）
/scope all - 监控全部版块
/scope <slug1,slug2> - 用 slug 设置版块，例如：/scope trade,inner
/targets - 查看当前推送目标
/addtarget - 将当前聊天加入推送目标
/target <chat_id> - 手动添加一个推送目标
/deltarget <目标ID> - 删除一个推送目标
/history - 查看最近命中的帖子
/status - 查看当前配置
/pause - 暂停提醒
/resume - 恢复提醒
/chatid - 查看当前聊天 ID

版块 slug：
daily, tech, info, review, trade, carpool, promo, life, dev, photo-share, expose, inner, sandbox

说明：
1. 每个关键词都独立管理，命中任意一个已启用关键词就会提醒。
2. 默认第一次使用会跳过旧帖，只从后续新帖开始通知。
3. 默认会把你第一次对话的当前聊天加入推送目标。
4. 每个用户最多可配置多个推送目标，默认上限是 10 个。
""".strip()


def _split_keywords(payload: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for part in payload.split(","):
        keyword = part.strip()
        normalized = keyword.lower()
        if not keyword or normalized in seen:
            continue
        seen.add(normalized)
        result.append(keyword)
    return result


def _chat_display_name(chat_title: str | None, chat_type: str | None, chat_id: int) -> str:
    if chat_title:
        return chat_title
    if chat_type == "private":
        return f"私聊 {chat_id}"
    return str(chat_id)


@dataclass(slots=True)
class BotHandlers:
    settings: Settings
    db: Database

    async def ensure_user(self, update: Update) -> UserRecord | None:
        if not update.effective_user or not update.effective_chat:
            raise RuntimeError("当前更新没有用户信息")
        if self.settings.bot_owner_ids and update.effective_user.id not in self.settings.bot_owner_ids:
            if update.effective_message:
                await update.effective_message.reply_text("这个 Bot 当前未开放给你使用。")
            return None

        chat = update.effective_chat
        if chat.type == "private":
            chat_title = update.effective_user.full_name
        else:
            chat_title = chat.title

        return await self.db.ensure_user_profile(
            tg_user_id=update.effective_user.id,
            chat_id=chat.id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
            chat_title=chat_title,
            chat_type=chat.type,
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        context.user_data.pop("awaiting_keyword", None)
        await update.effective_message.reply_text(
            MAIN_MENU_TEXT,
            reply_markup=build_main_menu(),
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        await update.effective_message.reply_text(HELP_TEXT, reply_markup=build_main_menu())

    async def chatid(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        await update.effective_message.reply_text(f"当前聊天 ID：{update.effective_chat.id}")

    async def addkw(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_message or not update.effective_user:
            return
        payload = update.effective_message.text.partition(" ")[2].strip()
        if not payload:
            await update.effective_message.reply_text(
                "请用：/addkw <关键词>\n例如：/addkw oracle"
            )
            return
        await self._add_keywords_from_text(update, update.effective_user.id, payload)

    async def keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_message or not update.effective_user:
            return

        payload = update.effective_message.text.partition(" ")[2].strip()
        if payload:
            first = payload.split()[0]
            if first.isdigit():
                await update.effective_message.reply_text(
                    "关键词命令已经改版了。\n"
                    "现在请用：/keywords 查看列表，或 /keywords 词1,词2 直接新增关键词。"
                )
                return
            await self._add_keywords_from_text(update, update.effective_user.id, payload)
            return

        keywords = await self.db.list_keywords_by_tg_user(update.effective_user.id)
        if not keywords:
            await update.effective_message.reply_text(
                "你还没有关键词。\n可以直接发：/keywords oracle,免费鸡,甲骨文"
            )
            return

        lines = ["我的关键词："]
        for keyword in keywords:
            status = "开启" if keyword.enabled else "关闭"
            lines.append(
                f"{keyword.id}. {keyword.keyword} [{status}] 命中 {keyword.hit_count} 次"
            )
        await update.effective_message.reply_text("\n".join(lines))

    async def _add_keywords_from_text(
        self,
        update: Update,
        tg_user_id: int,
        payload: str,
    ) -> None:
        if not update.effective_message:
            return
        keywords = _split_keywords(payload)
        if not keywords:
            await update.effective_message.reply_text("没有识别到有效关键词。")
            return

        current_count = await self.db.count_keywords_by_tg_user(tg_user_id)
        if current_count >= self.settings.max_keywords_per_user:
            await update.effective_message.reply_text(
                "你已经达到关键词数量上限。\n"
                f"当前上限：{self.settings.max_keywords_per_user} 个"
            )
            return

        added: list[str] = []
        duplicates: list[str] = []
        for keyword in keywords:
            if current_count >= self.settings.max_keywords_per_user:
                break
            success, record = await self.db.add_keyword(tg_user_id, keyword)
            if not success or record is None:
                duplicates.append(keyword)
                continue
            if record.keyword.lower() != keyword.strip().lower():
                duplicates.append(keyword)
                continue
            current_count += 1
            added.append(record.keyword)

        if added:
            text = "已添加关键词：\n" + "\n".join(f"- {item}" for item in added)
            if duplicates:
                text += "\n\n以下关键词已存在，已跳过：\n" + "\n".join(f"- {item}" for item in duplicates)
            await update.effective_message.reply_text(text)
            return

        await update.effective_message.reply_text("这些关键词都已经存在了，无需重复添加。")

    async def set_keyword_state(
        self,
        update: Update,
        enabled: bool,
    ) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_message or not update.effective_user:
            return
        payload = update.effective_message.text.partition(" ")[2].strip()
        if not payload or not payload.isdigit():
            command = "/on 1" if enabled else "/off 1"
            await update.effective_message.reply_text(f"请用：{command}")
            return

        changed = await self.db.set_keyword_enabled(
            update.effective_user.id,
            int(payload),
            enabled,
        )
        if not changed:
            await update.effective_message.reply_text("没有找到这个关键词 ID。")
            return
        await update.effective_message.reply_text("已开启。" if enabled else "已关闭。")

    async def on(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.set_keyword_state(update, True)

    async def off(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.set_keyword_state(update, False)

    async def delkw(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_message or not update.effective_user:
            return
        payload = update.effective_message.text.partition(" ")[2].strip()
        if not payload or not payload.isdigit():
            await update.effective_message.reply_text("请用：/delkw <关键词ID>\n例如：/delkw 1")
            return
        deleted = await self.db.delete_keyword(update.effective_user.id, int(payload))
        await update.effective_message.reply_text("已删除。" if deleted else "没有找到这个关键词 ID。")

    async def scope(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_message or not update.effective_user:
            return
        payload = update.effective_message.text.partition(" ")[2].strip()
        if not payload:
            await self._send_scope_selector(update.effective_message, update.effective_user.id)
            return

        if payload.lower() == "all":
            await self.db.set_user_categories(update.effective_user.id, [])
            await update.effective_message.reply_text("已设置为监控全部版块。")
            return

        slugs: list[str] = []
        invalid: list[str] = []
        for part in payload.split(","):
            slug = normalize_category_slug(part)
            if slug is None:
                invalid.append(part.strip())
            elif slug not in slugs:
                slugs.append(slug)

        if invalid:
            await update.effective_message.reply_text(
                "以下版块无法识别：\n" + "\n".join(f"- {item}" for item in invalid)
            )
            return

        await self.db.set_user_categories(update.effective_user.id, slugs)
        names = "、".join(category_label(item) for item in slugs)
        await update.effective_message.reply_text(f"已设置监控版块：{names}")

    async def _send_scope_selector(self, message, tg_user_id: int) -> None:
        settings = await self.db.get_user_settings_by_tg_user(tg_user_id)
        selected = {
            slug.strip()
            for slug in (settings.category_slugs if settings else "").split(",")
            if slug.strip()
        }
        await message.reply_text(
            "请选择要监控的版块（支持多选，不选表示全部版块）：",
            reply_markup=build_category_keyboard(selected),
        )

    async def scope_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not query or not update.effective_user:
            return
        if await self.ensure_user(update) is None:
            return

        data = query.data or ""
        settings = await self.db.get_user_settings_by_tg_user(update.effective_user.id)
        selected = {
            slug.strip()
            for slug in (settings.category_slugs if settings else "").split(",")
            if slug.strip()
        }

        if data == "scope:all":
            selected = set()
            await self.db.set_user_categories(update.effective_user.id, [])
            await query.answer("已切换为全部版块")
        elif data == "scope:done":
            if selected:
                names = "、".join(category_label(item) for item in CATEGORY_ORDER if item in selected)
                text = f"已保存版块设置：{names}"
            else:
                text = "已保存版块设置：全部版块"
            await query.edit_message_text(text)
            await query.answer()
            return
        elif data.startswith("scope:toggle:"):
            slug = data.split(":")[-1]
            if slug in selected:
                selected.remove(slug)
            else:
                selected.add(slug)
            await self.db.set_user_categories(
                update.effective_user.id,
                [item for item in CATEGORY_ORDER if item in selected],
            )
            await query.answer(category_label(slug))
        else:
            await query.answer()
            return

        await query.edit_message_reply_markup(reply_markup=build_category_keyboard(selected))

    async def targets(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_message or not update.effective_user:
            return
        targets = await self.db.list_targets_by_tg_user(update.effective_user.id)
        if not targets:
            await update.effective_message.reply_text("你还没有推送目标，可以先在当前聊天发送 /addtarget")
            return
        lines = ["当前推送目标："]
        for target in targets:
            lines.append(
                f"{target.id}. {_chat_display_name(target.chat_title, target.chat_type, target.chat_id)} ({target.chat_id})"
            )
        await update.effective_message.reply_text("\n".join(lines))

    async def addtarget(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = await self.ensure_user(update)
        if user is None or not update.effective_message or not update.effective_chat:
            return

        existing_targets = await self.db.list_targets_by_tg_user(user.tg_user_id)
        if any(item.chat_id == update.effective_chat.id for item in existing_targets):
            await update.effective_message.reply_text("当前聊天已经在推送目标列表里了。")
            return

        current_count = await self.db.count_targets_by_tg_user(user.tg_user_id)
        if current_count >= self.settings.max_targets_per_user:
            await update.effective_message.reply_text(
                "你已经达到推送目标上限。\n"
                f"当前上限：{self.settings.max_targets_per_user} 个"
            )
            return

        chat = update.effective_chat
        if chat.type == "private":
            chat_title = update.effective_user.full_name if update.effective_user else "私聊"
        else:
            chat_title = chat.title
        created = await self.db.add_target_by_tg_user(
            user.tg_user_id,
            chat.id,
            chat_title=chat_title,
            chat_type=chat.type,
        )
        if not created:
            await update.effective_message.reply_text("当前聊天已经在推送目标列表里了。")
            return
        await update.effective_message.reply_text(
            f"已添加推送目标：{_chat_display_name(chat_title, chat.type, chat.id)}"
        )

    async def target(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = await self.ensure_user(update)
        if user is None or not update.effective_message:
            return

        payload = update.effective_message.text.partition(" ")[2].strip()
        if not payload:
            await update.effective_message.reply_text("请用：/target <chat_id>")
            return
        try:
            chat_id = int(payload)
        except ValueError:
            await update.effective_message.reply_text("chat_id 必须是整数。")
            return

        existing_targets = await self.db.list_targets_by_tg_user(user.tg_user_id)
        if any(item.chat_id == chat_id for item in existing_targets):
            await update.effective_message.reply_text("这个 chat_id 已经存在于推送目标列表中。")
            return

        current_count = await self.db.count_targets_by_tg_user(user.tg_user_id)
        if current_count >= self.settings.max_targets_per_user:
            await update.effective_message.reply_text(
                f"你已经达到推送目标上限：{self.settings.max_targets_per_user} 个"
            )
            return

        created = await self.db.add_target_by_tg_user(
            user.tg_user_id,
            chat_id,
            chat_title=None,
            chat_type=None,
        )
        await update.effective_message.reply_text(
            "已添加推送目标。" if created else "这个 chat_id 已经存在于推送目标列表中。"
        )

    async def deltarget(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_message or not update.effective_user:
            return
        payload = update.effective_message.text.partition(" ")[2].strip()
        if not payload or not payload.isdigit():
            await update.effective_message.reply_text("请用：/deltarget <目标ID>")
            return
        deleted = await self.db.delete_target(update.effective_user.id, int(payload))
        await update.effective_message.reply_text("已删除。" if deleted else "没有找到这个目标 ID。")

    async def history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_message or not update.effective_user:
            return
        limit = self.settings.history_limit
        payload = update.effective_message.text.partition(" ")[2].strip()
        if payload.isdigit():
            limit = max(1, min(int(payload), 30))
        records = await self.db.list_history_by_tg_user(update.effective_user.id, limit)
        if not records:
            await update.effective_message.reply_text("还没有命中历史。")
            return

        lines = ["最近推送历史："]
        for index, record in enumerate(records, start=1):
            keywords = record.matched_keywords or "未知"
            category = category_label(record.category_slug)
            title = record.title or "历史记录"
            link = record.link or "(历史迁移记录，原链接不可用)"
            lines.append(
                f"{index}. {title}\n"
                f"⚡️ {keywords}\n"
                f"🏷️ {category}\n"
                f"🕒 {record.delivered_at}\n"
                f"🔗 {link}"
            )
        await update.effective_message.reply_text("\n\n".join(lines))

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_message or not update.effective_user:
            return
        settings = await self.db.get_user_settings_by_tg_user(update.effective_user.id)
        keywords = await self.db.list_keywords_by_tg_user(update.effective_user.id)
        targets = await self.db.list_targets_by_tg_user(update.effective_user.id)

        active_keywords = sum(1 for item in keywords if item.enabled)
        category_text = "全部版块"
        if settings and settings.category_slugs:
            selected = [slug for slug in CATEGORY_ORDER if slug in settings.category_slugs.split(",")]
            category_text = "、".join(category_label(slug) for slug in selected) if selected else "全部版块"

        lines = [
            "当前配置：",
            f"状态：{'启用' if settings and settings.enabled else '暂停'}",
            f"关键词：{len(keywords)} 个（启用 {active_keywords} 个）",
            f"版块：{category_text}",
            f"推送目标：{len(targets)} 个",
        ]
        await update.effective_message.reply_text("\n".join(lines))

    async def pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_user or not update.effective_message:
            return
        changed = await self.db.set_user_enabled(update.effective_user.id, False)
        await update.effective_message.reply_text("已暂停提醒。" if changed else "暂停失败。")

    async def resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_user or not update.effective_message:
            return
        changed = await self.db.set_user_enabled(update.effective_user.id, True)
        await update.effective_message.reply_text("已恢复提醒。" if changed else "恢复失败。")

    async def legacy_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self.status(update, context)

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_message or not update.effective_user:
            return

        text = (update.effective_message.text or "").strip()
        if text == "新建关键词":
            context.user_data["awaiting_keyword"] = True
            await update.effective_message.reply_text(
                "请输入关键词，多个关键词可用英文逗号分开。\n例如：oracle,免费鸡,megabox"
            )
            return
        if text == "我的关键词":
            await self.keywords(update, context)
            return
        if text == "版块设置":
            await self._send_scope_selector(update.effective_message, update.effective_user.id)
            return
        if text == "推送历史":
            await self.history(update, context)
            return
        if text == "添加当前聊天":
            await self.addtarget(update, context)
            return
        if text == "帮助":
            await self.help(update, context)
            return

        if context.user_data.get("awaiting_keyword"):
            context.user_data["awaiting_keyword"] = False
            await self._add_keywords_from_text(update, update.effective_user.id, text)


def build_application(settings: Settings, db: Database) -> Application:
    handlers = BotHandlers(settings=settings, db=db)
    application = Application.builder().token(settings.bot_token).build()
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help))
    application.add_handler(CommandHandler("chatid", handlers.chatid))
    application.add_handler(CommandHandler("keywords", handlers.keywords))
    application.add_handler(CommandHandler("addkw", handlers.addkw))
    application.add_handler(CommandHandler("on", handlers.on))
    application.add_handler(CommandHandler("off", handlers.off))
    application.add_handler(CommandHandler("delkw", handlers.delkw))
    application.add_handler(CommandHandler("scope", handlers.scope))
    application.add_handler(CommandHandler("targets", handlers.targets))
    application.add_handler(CommandHandler("addtarget", handlers.addtarget))
    application.add_handler(CommandHandler("target", handlers.target))
    application.add_handler(CommandHandler("deltarget", handlers.deltarget))
    application.add_handler(CommandHandler("history", handlers.history))
    application.add_handler(CommandHandler("status", handlers.status))
    application.add_handler(CommandHandler("pause", handlers.pause))
    application.add_handler(CommandHandler("resume", handlers.resume))
    application.add_handler(CommandHandler("list", handlers.legacy_list))
    application.add_handler(CallbackQueryHandler(handlers.scope_callback, pattern=r"^scope:"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text_message))
    return application
