# 🤖 Telegram 群管机器人

基于 **Python + aiogram 3** 的 Telegram 群管理机器人，支持入群验证、防广告防刷屏、敏感词过滤、管理员指令、群活跃统计，开箱即用，**Docker 一键部署**。

## ✨ 功能特性

| 功能 | 说明 |
| --- | --- |
| 👋 欢迎/欢送 | 新人入群自动欢迎、退群自动欢送，文案可自定义 |
| ✅ 入群验证码 | 新人须点击按钮验证，超时未验证自动移出群聊（防机器人/广告号） |
| 🚫 防广告 | 检测非白名单域名链接，删除 + 警告，累计 3 次自动禁言 1 小时 |
| 🌀 防刷屏 | 窗口时间内消息数超阈值自动禁言 |
| 🔤 敏感词过滤 | 命中自动删除 + 警告，累计 3 次禁言；词表按群管理 |
| 🛠 管理员指令 | 踢人 / 封禁 / 解封 / 禁言 / 解禁 / 删消息 / 置顶 |
| 📊 活跃统计 | 按自然日统计发言数，今日排行 TOP10 |
| 💾 数据持久化 | SQLite 本地存储，无需外部数据库，重启不丢配置 |

## 📁 项目结构

```
tg-group-manager-bot/
├── bot/
│   ├── main.py               # 入口
│   ├── config.py             # 环境变量配置
│   ├── database.py           # SQLite 存储层
│   ├── utils.py              # 权限判断 / 管理动作 / 工具函数
│   └── handlers/
│       ├── common.py         # /start /help
│       ├── welcome.py        # 欢迎 / 欢送
│       ├── captcha.py        # 入群验证码
│       ├── antispam.py       # 防广告 / 防刷屏
│       ├── wordfilter.py     # 敏感词过滤
│       ├── stats.py          # 活跃统计
│       └── admin.py          # 管理员指令
├── data/                     # SQLite 数据（Docker volume 持久化）
├── Dockerfile
├── docker-compose.yml
├── .env.example              # 配置模板（复制为 .env 后填写）
└── requirements.txt
```

## 🚀 快速开始（Docker）

### 第 1 步：创建机器人

1. 在 Telegram 里找到 **[@BotFather](https://t.me/BotFather)**，发送 `/newbot`，按提示取名，拿到形如 `123456789:AA...` 的 **token**。
2. 获取你的 Telegram 用户 ID（私聊 **[@userinfobot](https://t.me/userinfobot)** 即可看到）。

### 第 2 步：配置

```bash
cd tg-group-manager-bot
cp .env.example .env
# 编辑 .env，填写 BOT_TOKEN 和 ADMIN_IDS
```

`.env` 至少需要填两项：

```ini
BOT_TOKEN=123456789:AA...        # 你的机器人 token
ADMIN_IDS=12345678,87654321      # 超级管理员 ID，逗号分隔
```

### 第 3 步：启动

```bash
docker compose up -d --build
docker compose logs -f bot 2>/dev/null || docker compose logs -f    # 查看日志
```

看到 `机器人 @xxx 已启动` 即成功。停止：`docker compose down`。

### 第 4 步：配置群

1. 把机器人拉进你的群；
2. **在群设置中把机器人设为管理员**（授予删除消息、封禁用户等权限）——没有管理员权限，防广告/验证码/管理指令都无法生效；
3. 发送 `/help` 查看全部命令。

## 🖥 无 Docker 手动部署（可选）

```bash
cd tg-group-manager-bot
cp .env.example .env           # 填写 BOT_TOKEN / ADMIN_IDS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m bot.main
```

## ☁️ 部署到服务器

### 方式一：本机打包上传（推荐，无需在服务器拉代码）

**在本机执行：**

```bash
# 1. 打包（排除敏感配置与本地数据）
cd /path/to/tg-group-manager-bot
tar --exclude='.env' --exclude='data' --exclude='.venv' \
    --exclude='__pycache__' --exclude='*.pyc' \
    -czf tg-group-manager-bot.tar.gz .

# 2. 上传到服务器（替换为你的服务器 IP）
scp tg-group-manager-bot.tar.gz root@你的服务器IP:/root/
```

**在服务器上执行：**

```bash
# 3. 解压到部署目录
mkdir -p /opt/tg-bot && tar -xzf ~/tg-group-manager-bot.tar.gz -C /opt/tg-bot
cd /opt/tg-bot

# 4. 安装 Docker（Ubuntu / Debian，CentOS 用官方文档）
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# 5. 配置环境变量（填入 BOT_TOKEN / ADMIN_IDS）
cp .env.example .env
vim .env

# 6. 启动并查看日志
docker compose up -d --build
docker compose logs -f
```

看到 `机器人 @xxx 已启动` 即部署成功。

### 方式二：服务器直接 git clone

```bash
git clone <你的仓库地址> /opt/tg-bot && cd /opt/tg-bot
# 安装 Docker（同上）→ cp .env.example .env 填写 → docker compose up -d --build
```

### ⚠️ 国内服务器特别注意

Telegram API 在中国大陆网络下无法直连，**强烈建议服务器选海外节点**（新加坡、日本、美国等）。若服务器必须在国内，需要配置代理：

1. 在服务器上准备一个可用的 HTTP/SOCKS5 代理（如 `http://127.0.0.1:7890`）；
2. 在 `.env` 中配置：

```ini
PROXY=http://127.0.0.1:7890
```

3. 重启：`docker compose up -d --build`（依赖已包含 `aiohttp-socks`，无需额外安装）。

## 📖 命令手册

| 命令 | 说明 | 权限 |
| --- | --- | --- |
| `/help` | 显示命令手册 | 所有人 |
| `/stats` | 今日发言排行 TOP10 | 所有人 |
| `/mystats` | 我的今日发言数 | 所有人 |
| `/setwelcome 文案` | 设置欢迎语，支持 `{name}` `{username}` `{count}` | 管理员 |
| `/setfarewell 文案` | 设置欢送语，支持 `{name}` `{username}` | 管理员 |
| `/captcha on\|off` | 开关入群验证 | 管理员 |
| `/antispam on\|off` | 开关防广告/防刷屏 | 管理员 |
| `/kick` | 踢出（回复消息或 `/kick @用户名`） | 管理员 |
| `/ban` | 封禁 | 管理员 |
| `/unban` | 解封 | 管理员 |
| `/mute 5m` | 禁言，支持 `30s / 5m / 1h / 2d` | 管理员 |
| `/unmute` | 解除禁言 | 管理员 |
| `/del` | 删除消息（回复目标消息） | 管理员 |
| `/pin` | 置顶（回复目标消息） | 管理员 |
| `/unpin` | 取消置顶（回复目标消息） | 管理员 |
| `/addword 词` | 添加敏感词 | 管理员 |
| `/delword 词` | 删除敏感词 | 管理员 |
| `/listwords` | 查看敏感词列表 | 管理员 |
| `/resetstrikes` | 重置违规计次（回复目标用户） | 管理员 |

## ⚙️ 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `BOT_TOKEN` | （必填） | BotFather 获取的 token |
| `ADMIN_IDS` | （必填） | 超级管理员 ID，逗号分隔 |
| `DB_PATH` | `data/bot.db` | 数据库路径 |
| `CAPTCHA_ENABLED` | `true` | 是否默认开启入群验证 |
| `CAPTCHA_TIMEOUT` | `300` | 验证超时（秒） |
| `FLOOD_WINDOW` | `10` | 刷屏检测时间窗口（秒） |
| `FLOOD_THRESHOLD` | `5` | 窗口内消息数阈值 |
| `FLOOD_MUTE_SECONDS` | `600` | 刷屏禁言时长（秒） |
| `LINK_WHITELIST` | `t.me,...` | 链接白名单域名，逗号分隔 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `PROXY` | （空） | 网络代理（国内服务器必填），支持 http/https/socks5 |

## ⚠️ 部署注意事项

1. **机器人必须设为群管理员**，否则以下功能无法工作：入群验证、防广告、敏感词删除、踢人/禁言/封禁、置顶。
2. **入群验证**依赖 `chat_member` 更新事件，机器人需要管理员权限才能获取新成员加入事件。
3. **白名单域名**（如 `t.me`、`youtube.com`）默认不拦截，可在 `LINK_WHITELIST` 中按需增删。
4. 数据保存在 `data/bot.db`，已通过 volume 持久化；`docker compose down` 不会丢数据（`down -v` 才会清空 volume）。
5. 机器人通过**长轮询**（Long Polling）获取更新，无需公网 IP 或域名；如后续改用 Webhook，需自行配置 HTTPS 入口。
6. **国内服务器必须配置 `PROXY`** 才能连接 Telegram API；海外服务器无需配置。
7. 本项目仅包含标准群管理能力，请遵守所在地区的法律法规与 Telegram 社区准则。

## 🛠 常见问题

**Q：机器人不回复 / 功能没反应？**
- 检查 `.env` 的 `BOT_TOKEN` 是否填对；
- 确认机器人已被设为群管理员；
- 查看日志：`docker compose logs -f`。

**Q：为什么广告链接没被拦截？**
- 检查该域名是否在 `LINK_WHITELIST` 白名单里；
- 确认机器人有删除消息的管理员权限。

**Q：验证码一直显示"验证已过期"？**
- 通常是因为超时时间（`CAPTCHA_TIMEOUT`）内没点击，用户已被移出；可调大超时时间。

**Q：想全局禁用某个功能？**
- 在 `.env` 中把 `CAPTCHA_ENABLED` 设为 `false`，或在群里用 `/captcha off`、`/antispam off` 按群关闭。
