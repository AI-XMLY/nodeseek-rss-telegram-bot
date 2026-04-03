# NodeSeek RSS Telegram Bot

[简体中文](./README.md) | [English](./README.en.md)

一个面向 [NodeSeek RSS](https://rss.nodeseek.com/) 的轻量级 `RSS -> 关键词过滤 -> Telegram 推送` 机器人。

管理员部署一套共享 Bot，多位用户直接在 Telegram 里管理自己的 RSS、关键词和推送目标。

## 亮点

- 多用户共享 Bot
- Telegram 内自助订阅
- 每个用户支持多条 RSS
- 支持 `any` / `all` 关键词匹配
- 支持 HTML 富文本消息模板
- SQLite 持久化
- Docker 部署

## 快速开始

```bash
cp .env.example .env
```

在 `.env` 里填好 `BOT_TOKEN`，然后启动：

```bash
docker compose up -d --build
```

接着去 Telegram 给机器人发送：

```text
/start
/add https://rss.nodeseek.com/
/keywords 1 affman,oracle,免费鸡
/mode 1 any
/list
```

## 常用命令

- `/add <rss_url>`：添加一条 RSS 订阅
- `/keywords <订阅ID> <关键词1,关键词2>`：设置这条订阅的关键词
- `/mode <订阅ID> <any/all>`：设置匹配方式。`any` 表示命中任意一个关键词就推送，`all` 表示必须全部命中
- `/target <订阅ID> <目标chat_id>`：修改推送目标，可以发到私聊、群组或频道
- `/list`：查看你当前的全部订阅
- `/pause <订阅ID>`：暂停一条订阅
- `/resume <订阅ID>`：恢复一条订阅
- `/del <订阅ID>`：删除一条订阅
- `/chatid`：查看当前聊天的 chat_id，配置群组或频道推送时会用到

## 说明

- 推荐方式：源码放 GitHub，服务跑在一台 VPS 上，多个用户共用同一个 Bot。
- 默认首次拉取不补发旧内容，避免刷屏。
- 默认每个用户最多可创建 `20` 条订阅，可通过 `.env` 里的 `MAX_SUBSCRIPTIONS_PER_USER` 调整。

## 隐私说明

- 本项目会保存 Telegram 用户 ID、chat_id、用户名、订阅源、关键词和推送目标，仅用于完成订阅与推送。
- 这些数据默认保存在你自己服务器的 SQLite 数据库中，不会上传到 GitHub。
- 请勿公开 `.env` 和 `data/` 目录；如果 `BOT_TOKEN` 泄露，请立即在 BotFather 重置。
