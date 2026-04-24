# NodeSeek 关键词监控 Bot

监控 NodeSeek 关键词，命中新帖后自动推送到 Telegram。支持多用户共享、自部署、组合关键词、屏蔽词、版块多选、推送历史和去重推送。

## 功能介绍

- 关键词独立管理与开关
- 支持组合关键词，例如 `dmit + corona` 同时命中才提醒
- 支持屏蔽词，命中后不推送
- 支持版块多选
- 支持多目标推送配置，用户+社群最多10个；
- 支持推送历史
- 去重推送，重启后状态不丢失
- 多用户共享
- 默认 10 秒轮询一次 RSS，可在 `.env` 调整

常用命令：

- `/keywords`：查看我的关键词
- `/keywords <词1,词2>`：添加一个或多个关键词
- `/combo <词1,词2>`：添加组合关键词，所有词都命中才提醒
- `/on <关键词ID>`：开启关键词
- `/off <关键词ID>`：关闭关键词
- `/delkw <关键词ID>`：删除关键词
- `/block <词1,词2>`：添加屏蔽词，命中后不推送
- `/blocks`：查看屏蔽词
- `/delblock <屏蔽词ID>`：删除屏蔽词
- `/addtarget`：把当前聊天加入推送目标
- `/addtarget <chat_id>`：在私聊里绑定群组或频道
- `/targets`：查看推送目标
- `/deltarget <目标ID>`：删除推送目标
- `/history`：查看最近命中的帖子
- `/status`：查看当前配置
- `/pause`：暂停提醒
- `/resume`：恢复提醒

说明：

- 默认私聊可直接使用，不需要手动 `/addtarget`
- 群组里可直接发送 `/addtarget`
- 频道可在私聊里发送 `/addtarget <chat_id>` 进行绑定
- 群组或频道都要求操作者是管理员
- 如启用 `ALLOWED_USER_IDS`，只有白名单用户可以使用 Bot

## 可以先订阅我的机器人试试

https://t.me/NodeSeekKey_bot


## 个人部署教程

### 1. 准备 VPS 环境

在 VPS 上安装 Docker 和 Git：

```bash
apt update
apt install -y docker.io docker-compose-plugin git
```

### 2. 创建 Telegram Bot

在 Telegram 里找到 `@BotFather`，创建一个新的 Bot，并保存它给你的 `BOT_TOKEN`。

### 3. 下载项目

在 VPS 上执行：

```bash
git clone https://github.com/<你的用户名>/nodeseek-rss-telegram-bot.git
cd nodeseek-rss-telegram-bot
```

### 4. 配置环境变量

复制配置模板：

```bash
cp .env.example .env
nano .env
```

把 `.env` 里的 `BOT_TOKEN` 改成你自己的 Token。

如需启用白名单模式，可以额外配置：

```text
ALLOWED_USER_IDS=<用户ID1>,<用户ID2>
```

### 5. 启动 Bot

```bash
docker compose up -d --build
```

### 6. 查看运行日志

```bash
docker compose logs -f
```

看到 `Application started` 就说明启动成功了。

按 `Ctrl + C` 可以退出日志查看，不会停止 Bot。

### 7. 更新项目

如果只是普通更新，可以执行：

```bash
git pull
docker compose down
docker compose up -d --build
```

如果 VPS 提示 Git 分支冲突，可以改用强制对齐 GitHub：

```bash
git fetch origin
git reset --hard origin/main
docker compose down
docker compose up -d --build
```

## 隐私说明

- 本项目会保存 Telegram 用户 ID、chat_id、关键词、版块设置、推送目标和历史记录，仅用于提醒服务。
- 数据默认保存在部署者自己服务器上的 SQLite 数据库，不会上传到 GitHub。
- 请勿公开 `.env` 和 `data/` 目录；如果 `BOT_TOKEN` 泄露，请立即在 BotFather 重置。
