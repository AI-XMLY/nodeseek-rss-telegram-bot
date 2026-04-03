from __future__ import annotations

from dataclasses import dataclass

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.config import Settings
from app.db import Database


HELP_TEXT = """
可用命令：
/start - 注册并显示欢迎信息
/help - 查看帮助
/chatid - 查看当前聊天 ID
/add <rss_url> - 新建一条 RSS 订阅
/keywords <订阅ID> <关键词1,关键词2> - 设置关键词
/mode <订阅ID> <any/all> - 设置关键词匹配方式
/target <订阅ID> <目标chat_id> - 设置推送目标
/list - 查看你的全部订阅
/pause <订阅ID> - 暂停某条订阅
/resume <订阅ID> - 恢复某条订阅
/del <订阅ID> - 删除某条订阅

示例：
/add https://rss.nodeseek.com/
/keywords 1 affman,oracle,免费鸡
/mode 1 any
/target 1 -1001234567890
/list

说明：
1. `/add` 只负责添加 RSS，默认不设关键词，默认推送到当前聊天。
2. `/keywords` 用来设置关键词，多个关键词用英文逗号分开。
3. `/mode` 里 `any` 表示命中任意一个关键词就推送，`all` 表示必须全部命中。
4. `/target` 用来改推送目标；如果要发到群组或频道，先用 /chatid 获取目标 chat_id。
5. 每个用户的订阅数量有上限，默认是 20 条，可由管理员调整。
""".strip()


@dataclass(slots=True)
class BotHandlers:
    settings: Settings
    db: Database

    async def ensure_user(self, update: Update) -> int | None:
        if not update.effective_user or not update.effective_chat:
            raise RuntimeError("当前更新没有用户信息")
        if self.settings.bot_owner_ids and update.effective_user.id not in self.settings.bot_owner_ids:
            if update.effective_message:
                await update.effective_message.reply_text("这个 Bot 当前未开放给你使用。")
            return None
        user = await self.db.upsert_user(
            tg_user_id=update.effective_user.id,
            chat_id=update.effective_chat.id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
        )
        return user.id

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        await update.effective_message.reply_text(
            "欢迎使用 NodeSeek RSS 关键词推送机器人。\n\n"
            "推荐顺序：先 /add，再 /keywords，再 /mode，最后用 /list 查看结果。\n\n"
            f"{HELP_TEXT}"
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        await update.effective_message.reply_text(HELP_TEXT)

    async def chatid(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        await update.effective_message.reply_text(f"当前聊天 ID：{update.effective_chat.id}")

    async def add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = await self.ensure_user(update)
        if user_id is None:
            return
        if not update.effective_message or not update.effective_chat or not update.effective_user:
            return

        text = update.effective_message.text or ""
        payload = text.partition(" ")[2].strip()
        if not payload:
            await update.effective_message.reply_text(
                "请用：/add <rss_url>\n"
                "例如：/add https://rss.nodeseek.com/"
            )
            return

        current_count = await self.db.count_subscriptions_by_tg_user(update.effective_user.id)
        if current_count >= self.settings.max_subscriptions_per_user:
            await update.effective_message.reply_text(
                "你已经达到订阅数量上限。\n"
                f"当前上限：{self.settings.max_subscriptions_per_user} 条\n"
                "如果需要新增，请先删除一些旧订阅。"
            )
            return

        if "|" in payload:
            await self._add_legacy(update, user_id, payload)
            return

        feed_url = payload
        if not feed_url.startswith("http://") and not feed_url.startswith("https://"):
            await update.effective_message.reply_text("RSS 地址必须以 http:// 或 https:// 开头。")
            return

        target_chat_id = self.settings.default_target_chat_id or update.effective_chat.id
        subscription_id = await self.db.add_subscription(
            user_id=user_id,
            feed_url=feed_url,
            keywords="",
            match_mode="any",
            target_chat_id=target_chat_id,
        )
        await update.effective_message.reply_text(
            "订阅已创建。\n"
            f"ID：{subscription_id}\n"
            f"RSS：{feed_url}\n"
            f"关键词：未设置\n"
            f"模式：any\n"
            f"推送 chat_id：{target_chat_id}\n\n"
            "下一步你可以继续发：\n"
            f"/keywords {subscription_id} affman,oracle,免费鸡\n"
            f"/mode {subscription_id} any\n"
            f"/target {subscription_id} -1001234567890"
        )

    async def _add_legacy(self, update: Update, user_id: int, payload: str) -> None:
        if not update.effective_message or not update.effective_chat:
            return
        parts = [part.strip() for part in payload.split("|")]
        feed_url = parts[0] if len(parts) >= 1 else ""
        keywords = parts[1] if len(parts) >= 2 else ""
        match_mode = (parts[2] if len(parts) >= 3 else "any").lower()
        target_chat_id_raw = parts[3] if len(parts) >= 4 else ""

        if not feed_url.startswith("http://") and not feed_url.startswith("https://"):
            await update.effective_message.reply_text("RSS 地址必须以 http:// 或 https:// 开头。")
            return

        if match_mode not in {"any", "all"}:
            await update.effective_message.reply_text("匹配模式只能是 any 或 all。")
            return

        if target_chat_id_raw:
            try:
                target_chat_id = int(target_chat_id_raw)
            except ValueError:
                await update.effective_message.reply_text("目标 chat_id 必须是整数。")
                return
        else:
            target_chat_id = self.settings.default_target_chat_id or update.effective_chat.id

        subscription_id = await self.db.add_subscription(
            user_id=user_id,
            feed_url=feed_url,
            keywords=keywords,
            match_mode=match_mode,
            target_chat_id=target_chat_id,
        )
        await update.effective_message.reply_text(
            "订阅已创建。你用了兼容旧格式的一行写法。\n"
            f"ID：{subscription_id}\n"
            f"RSS：{feed_url}\n"
            f"关键词：{keywords or '未设置'}\n"
            f"模式：{match_mode}\n"
            f"推送 chat_id：{target_chat_id}\n\n"
            "以后也可以改用更简单的分步命令：/add、/keywords、/mode、/target"
        )

    async def keywords(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_user or not update.effective_message:
            return

        payload = update.effective_message.text.partition(" ")[2].strip()
        if not payload:
            await update.effective_message.reply_text(
                "请用：/keywords <订阅ID> <关键词1,关键词2>\n"
                "例如：/keywords 1 affman,oracle,免费鸡\n"
                "如果想清空关键词，可以用：/keywords 1 clear"
            )
            return

        subscription_id_raw, _, keywords = payload.partition(" ")
        if not subscription_id_raw or not keywords.strip():
            await update.effective_message.reply_text(
                "请用：/keywords <订阅ID> <关键词1,关键词2>"
            )
            return

        try:
            subscription_id = int(subscription_id_raw)
        except ValueError:
            await update.effective_message.reply_text("订阅 ID 必须是整数。")
            return

        normalized = "" if keywords.strip().lower() == "clear" else keywords.strip()
        updated = await self.db.update_subscription_keywords(
            subscription_id,
            update.effective_user.id,
            normalized,
        )
        if not updated:
            await update.effective_message.reply_text("没有找到这条订阅。")
            return

        await update.effective_message.reply_text(
            f"关键词已更新：{normalized or '未设置'}"
        )

    async def mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_user or not update.effective_message:
            return

        args = update.effective_message.text.partition(" ")[2].strip().split()
        if len(args) != 2:
            await update.effective_message.reply_text(
                "请用：/mode <订阅ID> <any/all>\n例如：/mode 1 any"
            )
            return

        try:
            subscription_id = int(args[0])
        except ValueError:
            await update.effective_message.reply_text("订阅 ID 必须是整数。")
            return

        match_mode = args[1].lower()
        if match_mode not in {"any", "all"}:
            await update.effective_message.reply_text("匹配模式只能是 any 或 all。")
            return

        updated = await self.db.update_subscription_match_mode(
            subscription_id,
            update.effective_user.id,
            match_mode,
        )
        if not updated:
            await update.effective_message.reply_text("没有找到这条订阅。")
            return

        await update.effective_message.reply_text(
            "匹配模式已更新：任意关键词命中即推送" if match_mode == "any" else "匹配模式已更新：必须全部关键词命中才推送"
        )

    async def target(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_user or not update.effective_message:
            return

        args = update.effective_message.text.partition(" ")[2].strip().split()
        if len(args) != 2:
            await update.effective_message.reply_text(
                "请用：/target <订阅ID> <目标chat_id>\n例如：/target 1 -1001234567890"
            )
            return

        try:
            subscription_id = int(args[0])
            target_chat_id = int(args[1])
        except ValueError:
            await update.effective_message.reply_text("订阅 ID 和 chat_id 都必须是整数。")
            return

        updated = await self.db.update_subscription_target_chat(
            subscription_id,
            update.effective_user.id,
            target_chat_id,
        )
        if not updated:
            await update.effective_message.reply_text("没有找到这条订阅。")
            return

        await update.effective_message.reply_text(f"推送目标已更新：{target_chat_id}")

    async def list_subs(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_user or not update.effective_message:
            return
        subscriptions = await self.db.list_subscriptions_by_tg_user(update.effective_user.id)
        if not subscriptions:
            await update.effective_message.reply_text("你还没有订阅。先用 /add 添加一条。")
            return

        lines = []
        for sub in subscriptions:
            lines.append(
                "\n".join(
                    [
                        f"ID：{sub.id}",
                        f"状态：{'启用' if sub.enabled else '暂停'}",
                        f"RSS：{sub.feed_url}",
                        f"来源：{sub.feed_title or '尚未拉取'}",
                        f"关键词：{sub.keywords or '未设置'}",
                        f"模式：{sub.match_mode}",
                        f"目标 chat_id：{sub.target_chat_id}",
                    ]
                )
            )
        await update.effective_message.reply_text("\n\n".join(lines))

    async def pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._toggle_subscription(update, enabled=False)

    async def resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await self._toggle_subscription(update, enabled=True)

    async def delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_user or not update.effective_message:
            return
        if not context.args:
            await update.effective_message.reply_text("请提供订阅 ID，例如：/del 1")
            return

        try:
            subscription_id = int(context.args[0])
        except ValueError:
            await update.effective_message.reply_text("订阅 ID 必须是整数。")
            return

        deleted = await self.db.delete_subscription(subscription_id, update.effective_user.id)
        await update.effective_message.reply_text("删除成功。" if deleted else "没有找到这条订阅。")

    async def _toggle_subscription(
        self,
        update: Update,
        *,
        enabled: bool,
    ) -> None:
        if await self.ensure_user(update) is None:
            return
        if not update.effective_user or not update.effective_message:
            return
        args = update.effective_message.text.partition(" ")[2].strip().split()
        if not args:
            await update.effective_message.reply_text(
                f"请提供订阅 ID，例如：{'/resume 1' if enabled else '/pause 1'}"
            )
            return

        try:
            subscription_id = int(args[0])
        except ValueError:
            await update.effective_message.reply_text("订阅 ID 必须是整数。")
            return

        changed = await self.db.set_subscription_enabled(subscription_id, update.effective_user.id, enabled)
        if not changed:
            await update.effective_message.reply_text("没有找到这条订阅。")
            return
        await update.effective_message.reply_text("已恢复。" if enabled else "已暂停。")


def build_application(settings: Settings, db: Database) -> Application:
    handlers = BotHandlers(settings=settings, db=db)
    application = Application.builder().token(settings.bot_token).build()
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help))
    application.add_handler(CommandHandler("chatid", handlers.chatid))
    application.add_handler(CommandHandler("add", handlers.add))
    application.add_handler(CommandHandler("keywords", handlers.keywords))
    application.add_handler(CommandHandler("mode", handlers.mode))
    application.add_handler(CommandHandler("target", handlers.target))
    application.add_handler(CommandHandler("list", handlers.list_subs))
    application.add_handler(CommandHandler("pause", handlers.pause))
    application.add_handler(CommandHandler("resume", handlers.resume))
    application.add_handler(CommandHandler("del", handlers.delete))
    return application
