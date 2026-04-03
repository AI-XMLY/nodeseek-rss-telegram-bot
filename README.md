# NodeSeek RSS Telegram Bot

一个专门为 `RSS -> 关键词过滤 -> Telegram 自动推送` 场景准备的开源项目，默认适配你提到的 `https://rss.nodeseek.com/`。

它支持：

- 多用户使用同一个 Bot
- 每个用户都能在 Telegram 里单独配置自己的订阅源、关键词、推送目标
- 每个用户可添加多条 RSS 订阅
- 每条订阅都可设置独立关键词
- 支持 `any` / `all` 两种关键词匹配模式
- 消息支持 HTML 富文本模板自定义
- 标题优先使用 RSS 帖子标题，适合 NodeSeek 帖子推送
- SQLite 持久化
- Docker / Docker Compose 一键部署
- 首次订阅默认不补发历史消息，避免刷屏

## 项目灵感

这个项目的设计思路参考了这些优秀开源项目：

- [Rongronggg9/RSS-to-Telegram-Bot](https://github.com/Rongronggg9/RSS-to-Telegram-Bot)
- [indes/flowerss-bot](https://github.com/indes/flowerss-bot)
- [mez0ru/RSS-Telegram-Bot](https://github.com/mez0ru/RSS-Telegram-Bot)

但实现上我把范围收得更聚焦一些，优先满足你现在最需要的能力：

`NodeSeek RSS -> 关键词过滤 -> Telegram 自动推送`

## 适合谁

如果你想把项目推广到 GitHub，同时又想让 Bot 稳定在线，最推荐的方式是：

`GitHub 放源码 + VPS 跑 Docker Compose`

原因很简单：

- GitHub 更适合展示、推广、收 star、收 issue
- VPS 更适合长期运行 Telegram Bot
- 比把 Bot 直接跑在 GitHub Actions 上稳定得多
- 不怕 Action 定时器延迟或任务中断
- SQLite 存储更自然，维护也轻松

所以这个项目的最佳实践不是“只部署到 GitHub”，而是：

1. GitHub：放源码、README、截图、更新记录
2. VPS：真正运行机器人

这样最适合你去 NodeSeek 推广。

## 多用户到底怎么工作

这部分单独说清楚一下，因为这正是你最关心的点。

这个项目不是“机器人主人在服务器里写死关键词”，而是：

- 每个 Telegram 用户都可以直接和 Bot 对话
- 每个用户都能自己发送 `/add`
- 每个用户都能添加自己的 RSS 地址
- 每个用户都能设置自己的关键词
- 每个用户都能决定 `any` 还是 `all`
- 每个用户都能查看、暂停、恢复、删除自己的订阅

也就是说：

- 用户 A 配置 `oracle,免费鸡`
- 用户 B 配置 `搬瓦工,香港`
- 用户 C 甚至可以订阅另一个 RSS

这些配置都会分别存进 SQLite，不会混在一起。

对应实现可以看：

- [app/bot.py](/Users/ethan/Documents/Codex/TG%20订阅机器人/app/bot.py#L39)
- [app/db.py](/Users/ethan/Documents/Codex/TG%20订阅机器人/app/db.py#L89)
- [app/db.py](/Users/ethan/Documents/Codex/TG%20订阅机器人/app/db.py#L144)

如果你只想允许你自己先测试，也可以在 `.env` 里设置：

```text
BOT_OWNER_IDS=你的TG用户ID
```

等测试完成后，把它留空，就会变成公开多用户 Bot。

## 功能截图式理解

你可以把它理解为：

1. Bot 每隔几分钟抓一次 RSS
2. 拿到每篇帖子后，检查标题和摘要里有没有你关心的关键词
3. 命中后，按你自定义的 HTML 模板发到 Telegram
4. 发过的内容会记录到 SQLite，避免重复推送

## 命令列表

启动 Bot 后，在 Telegram 里可以使用这些命令：

- `/start`
- `/help`
- `/chatid`
- `/add <rss_url> | <关键词1,关键词2> | <any/all> | <目标chat_id>`
- `/list`
- `/pause <订阅ID>`
- `/resume <订阅ID>`
- `/del <订阅ID>`

示例：

```text
/add https://rss.nodeseek.com/ | affman,oracle,免费鸡 | any
/add https://rss.nodeseek.com/ | 搬瓦工,甲骨文 | all
/add https://rss.nodeseek.com/ | VPS,杜甫 | any | -1001234567890
```

说明：

- 关键词留空时，表示这个订阅不过滤，全部推送
- `any` 表示命中任意一个关键词就推送
- `all` 表示必须所有关键词都命中才推送
- 不写 `chat_id` 时，默认推送到你当前和 Bot 的私聊窗口

## 消息模板

默认模板在 `.env` 里：

```text
MESSAGE_TEMPLATE=<b>{title}</b>\n\n{summary}\n\n关键词：<code>{matched_keywords}</code>\n发布时间：<code>{published_at}</code>\n<a href="{link}">打开原帖</a>\n<i>{feed_title}</i>
```

可用变量：

- `{title}`：RSS 文章标题
- `{summary}`：摘要，已自动去 HTML 标签
- `{matched_keywords}`：本次命中的关键词
- `{published_at}`：发布时间
- `{link}`：原帖链接
- `{feed_title}`：RSS 来源标题

这意味着你可以很方便地把 NodeSeek 帖子标题放在最醒目的位置。

## 一步步安装：适合小白

下面假设你的 VPS 是一台全新的 Linux 机器。

### 第 1 步：创建 Telegram Bot

1. 打开 Telegram，搜索 `@BotFather`
2. 发送 `/newbot`
3. 按提示设置机器人名字和用户名
4. 创建成功后，BotFather 会给你一个 `BOT_TOKEN`
5. 先把这个 token 保存好，后面要用

### 第 2 步：登录你的 VPS

在你自己的电脑终端里执行：

```bash
ssh root@你的VPS_IP
```

如果你不是 root 用户，就把 `root` 换成你自己的用户名。

### 第 3 步：安装 Docker 和 Docker Compose

如果你的 VPS 是 Ubuntu，直接执行：

```bash
apt update
apt install -y docker.io docker-compose-plugin git
systemctl enable docker
systemctl start docker
```

检查 Docker 是否安装成功：

```bash
docker --version
docker compose version
```

### 第 4 步：先把项目发布到 GitHub

这是你后面去 NodeSeek 推广时最重要的一步。

先在 GitHub 新建一个仓库，建议名字直接叫：

```text
nodeseek-rss-telegram-bot
```

仓库建议填写：

- Repository name: `nodeseek-rss-telegram-bot`
- Description: `RSS to Telegram bot with keyword filtering, multi-user subscriptions, SQLite and Docker support`
- Visibility: `Public`

然后在你的本地项目目录执行：

```bash
git init
git add .
git commit -m "feat: initial release"
git branch -M main
git remote add origin 你的GitHub仓库地址
git push -u origin main
```

推上去之后，你就已经拥有一个可以公开展示的 GitHub 项目页了。

### 第 5 步：再把 GitHub 项目拉到 VPS

```bash
git clone 你的仓库地址 nodeseek-rss-bot
cd nodeseek-rss-bot
```

### 第 6 步：配置环境变量

先复制一份配置文件：

```bash
cp .env.example .env
```

然后编辑：

```bash
nano .env
```

你最少只需要改这几个：

```text
BOT_TOKEN=替换成你的BotFather token
DATABASE_PATH=data/bot.db
POLL_INTERVAL_SECONDS=180
MARK_AS_READ_ON_FIRST_POLL=true
```

如果你想修改推送格式，也可以改：

```text
MESSAGE_TEMPLATE=<b>{title}</b>\n\n{summary}\n\n关键词：<code>{matched_keywords}</code>\n发布时间：<code>{published_at}</code>\n<a href="{link}">打开原帖</a>\n<i>{feed_title}</i>
```

### 第 7 步：启动

第一次启动：

```bash
docker compose up -d --build
```

查看运行状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f
```

如果日志里没有报错，说明机器人已经跑起来了。

### 第 8 步：在 Telegram 里开始使用

1. 打开你刚创建的 Bot
2. 发送 `/start`
3. 添加一条 NodeSeek RSS 订阅

例如：

```text
/add https://rss.nodeseek.com/ | affman,oracle,免费鸡 | any
```

再比如：

```text
/add https://rss.nodeseek.com/ | 搬瓦工,甲骨文 | all
```

查看当前订阅：

```text
/list
```

暂停某条：

```text
/pause 1
```

恢复某条：

```text
/resume 1
```

删除某条：

```text
/del 1
```

## 如果你想推送到群组或频道

思路是这样：

1. 先把 Bot 拉进群组或频道
2. 给它发送消息权限
3. 获取这个群组或频道的 `chat_id`
4. 在 `/add` 命令最后一段填入这个 `chat_id`

比如：

```text
/add https://rss.nodeseek.com/ | Oracle,免费鸡 | any | -1001234567890
```

`-100` 开头通常是频道或超级群的 ID。

## 本地直接运行方式

如果你暂时不想用 Docker，也可以直接跑 Python。

### 1. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

填好 `BOT_TOKEN` 后启动：

```bash
python -m app.main
```

## 常见问题

### 为什么我还是推荐“GitHub + VPS”，而不是只用 GitHub？

因为 GitHub 最适合做这些事情：

- 展示源码
- 收 star
- 写 README
- 发 release
- 跑 CI 检查

但它不适合长期稳定跑一个 RSS 轮询机器人。

如果你硬要把机器人主程序跑在 GitHub Actions 上，会遇到这些问题：

- 定时不够稳定
- 容易超时
- 状态持久化麻烦
- SQLite 不适合作为 Actions 的长期运行数据盘

所以最稳妥的方案依然是：

- GitHub 负责“推广和展示”
- VPS 负责“实际运行”

这也是开源 Bot 项目里最常见的做法。

### 推广时 GitHub 首页怎么写更吸引人？

你可以直接把仓库副标题写成：

```text
NodeSeek RSS -> Keyword Filter -> Telegram Push Bot
```

或者：

```text
Telegram RSS bot for NodeSeek with keyword filtering, multi-user subscriptions, SQLite and Docker support
```

### 为什么刚加订阅没有立刻收到一堆旧消息？

因为默认开启了：

```text
MARK_AS_READ_ON_FIRST_POLL=true
```

这样做是为了防止第一次就把历史文章全部刷给你。

如果你想让它第一次就尝试推送当前 RSS 中的文章，可以改成：

```text
MARK_AS_READ_ON_FIRST_POLL=false
```

### 关键词匹配检查哪些内容？

目前会检查：

- 标题
- 摘要
- 标签

### 数据存在哪里？

默认保存在：

```text
data/bot.db
```

这是 SQLite 文件。

### Docker 重启后数据会丢吗？

不会。

因为 `docker-compose.yml` 里已经把本地 `./data` 映射到了容器里的 `/app/data`。

## 项目结构

```text
.
├── app
│   ├── bot.py
│   ├── config.py
│   ├── db.py
│   ├── formatter.py
│   ├── main.py
│   ├── poller.py
│   ├── rss.py
│   └── utils.py
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── LICENSE
├── README.md
└── requirements.txt
```

## 后续你还可以怎么扩展

如果你之后想继续升级，这个项目也很适合继续加功能：

- 黑名单关键词
- 正则匹配
- OPML 导入导出
- Web 管理面板
- 多语言
- 按订阅自定义消息模板
- 支持 PostgreSQL

## 许可协议

MIT
