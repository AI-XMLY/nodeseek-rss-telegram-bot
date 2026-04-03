# NodeSeek RSS Telegram Bot

[English](./README.md) | [简体中文](./README.zh-CN.md)

一个面向 [NodeSeek RSS](https://rss.nodeseek.com/) 的轻量级 `RSS -> 关键词过滤 -> Telegram 推送` 机器人。

支持多用户在 Telegram 内自助管理订阅、每个用户多条 RSS、`any/all` 关键词匹配、HTML 富文本消息模板、SQLite 持久化和 Docker 部署。

## 快速开始

```bash
cp .env.example .env
docker compose up -d --build
```

在 `.env` 里填好 `BOT_TOKEN`，然后到 Telegram 里发送：

```text
/start
/add https://rss.nodeseek.com/ | affman,oracle,免费鸡 | any
/list
```

## 常用命令

- `/add <rss_url> | <关键词1,关键词2> | <any/all> | <目标chat_id>`
- `/list`
- `/pause <订阅ID>`
- `/resume <订阅ID>`
- `/del <订阅ID>`
- `/chatid`

## 说明

- 每个 Telegram 用户都可以独立管理自己的订阅源和关键词。
- 默认首次拉取不会补发旧内容，避免刷屏。
- 推荐部署方式：`GitHub 放源码 + VPS 跑服务`。

