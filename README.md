# NodeSeek 关键词监控 Bot

监控 NodeSeek 关键词，命中新帖后自动推送到 Telegram。支持多用户共享、自部署、关键词开关、版块多选、推送历史和去重推送。

## 功能介绍

- 关键词独立管理与开关
- 支持版块多选
- 支持多目标推送配置，用户+社群最多10个；
- 支持推送历史
- 去重推送，重启后状态不丢失
- 多用户共享

常用命令：

- `/keywords`：查看我的关键词
- `/keywords <词1,词2>`：添加一个或多个关键词
- `/on <关键词ID>`：开启关键词
- `/off <关键词ID>`：关闭关键词
- `/delkw <关键词ID>`：删除关键词
- `/addtarget`：把当前聊天加入推送目标
- `/targets`：查看推送目标
- `/deltarget <目标ID>`：删除推送目标
- `/history`：查看最近命中的帖子
- `/status`：查看当前配置
- `/pause`：暂停提醒
- `/resume`：恢复提醒

说明：

- 默认私聊可直接使用，不需要手动 `/addtarget`
- 群组或频道里只有管理员才能执行 `/addtarget`
- 如启用 `ALLOWED_USER_IDS`，只有白名单用户可以使用 Bot


## 个人部署教程

1. VPS安装 Docker 和 Git：

```bash
apt update
apt install -y docker.io docker-compose-plugin git
```

2. 去 Telegram 找 `@BotFather` 创建 Bot，拿到 `BOT_TOKEN`

3. 在 VPS 上下载项目：

```bash
git clone https://github.com/<你的用户名>/nodeseek-rss-telegram-bot.git
cd nodeseek-rss-telegram-bot
```

4. 创建配置文件：

```bash
cp .env.example .env
nano .env
```

把 `BOT_TOKEN` 改成你自己的。

如需启用白名单模式，可以额外配置：

```text
ALLOWED_USER_IDS=<用户ID1>,<用户ID2>
```

5. 启动 Bot：

```bash
docker compose up -d --build
```

6. 查看是否成功：

```bash
docker compose logs -f
```

看到 `Application started` 就说明启动成功了。

7. 更新项目：

```bash
git pull
docker compose down
docker compose up -d --build
```

## 隐私说明

- 本项目会保存 Telegram 用户 ID、chat_id、关键词、版块设置、推送目标和历史记录，仅用于提醒服务。
- 数据默认保存在部署者自己服务器上的 SQLite 数据库，不会上传到 GitHub。
- 请勿公开 `.env` 和 `data/` 目录；如果 `BOT_TOKEN` 泄露，请立即在 BotFather 重置。
