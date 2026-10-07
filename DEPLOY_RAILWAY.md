# Railway 部署详细教程（Telegram 群管机器人）

> 代码已上传到 GitHub 仓库：`https://github.com/mikeevan0404/mike`
> 本教程从零开始，把机器人部署到 Railway 并跑起来，全程网页操作，约 10 分钟。

---

## 0. 前置准备（5 分钟）

部署前确认这三样东西齐了：

| 项目 | 说明 | 获取方式 |
| --- | --- | --- |
| GitHub 账号 | 已登录，代码已在 `mikeevan0404/mike` 仓库 | ✅ 已完成 |
| 机器人 Token | 形如 `123456789:AAxxxxxx` | Telegram 里找 @BotFather → `/newbot` 创建，创建时会给 |
| 你的 Telegram 用户 ID | 纯数字，如 `12345678` | Telegram 里私聊 @userinfobot 它会直接回复你的 ID |

> ⚠️ **重要**：`railway.app` 和 `github.com` 在中国大陆网络下需要**科学上网**才能访问，请先确保浏览器能打开这两个网站。

---

## 1. 登录 Railway

1. 浏览器打开 **https://railway.app**
2. 点右上角 **Start a New Project**（或页面上 **Login**）
3. 选择 **Continue with GitHub**（用 GitHub 账号登录）
4. 跳转到 GitHub 授权页，点绿色的 **Authorize Railway**，跳回 Railway 即登录成功

---

## 2. 从 GitHub 导入并部署（核心步骤）

1. 登录后首页点 **New Project**（新建项目）
2. 在弹出的面板选 **Deploy from GitHub repo**（从 GitHub 仓库部署）
3. 首次使用需要先授权：页面提示 **Install GitHub App** → 点进去 → 选择 **Only select repositories**（仅选择仓库）→ 勾选 **mike** 这个仓库 → 点 **Install** 授权
4. 回到部署面板，**mike** 仓库应该出现在列表里 → 点击它 → 点 **Deploy Now**（立即部署）
5. 部署开始后，页面进入项目详情，顶部 **Deployments** 标签里能看到构建过程：
   - `BUILD` 阶段：Railway 自动识别项目根目录的 `Dockerfile`，安装 Python 依赖
   - `DEPLOY` 阶段：容器启动，运行 `python -m bot.main`
   - 首次构建需要 1~3 分钟，耐心等待

> 如果仓库列表里找不到 mike：点仓库列表右下角的 **Configure GitHub App** → 重新确认仓库授权。

---

## 3. 配置环境变量（必做，否则机器人无法启动）

1. 在项目详情页顶部点 **Variables**（变量）标签
2. 点 **New Variable**（新建变量），逐条添加：

| 变量名 | 值 | 必填 |
| --- | --- | --- |
| `BOT_TOKEN` | 你的机器人 Token（@BotFather 获取） | ✅ 必填 |
| `ADMIN_IDS` | 你的 Telegram 用户 ID | ✅ 必填 |
| `CAPTCHA_ENABLED` | `true` | 可选（默认开） |
| `CAPTCHA_TIMEOUT` | `300` | 可选（验证超时秒数） |
| `FLOOD_WINDOW` | `10` | 可选（防刷屏窗口秒数） |
| `FLOOD_THRESHOLD` | `5` | 可选（刷屏阈值） |
| `FLOOD_MUTE_SECONDS` | `600` | 可选（刷屏禁言时长） |
| `LINK_WHITELIST` | `t.me,telegram.me,...` | 可选（链接白名单） |

3. 添加完 Variables 后，服务**会自动重启**一次，等它重启完成

> ⚠️ `BOT_TOKEN` 和 `ADMIN_IDS` 不填，机器人启动会直接报错退出。
> Railway 服务器在海外，**不需要**配置 `PROXY`，直连 Telegram。

---

## 4. 挂载 Volume（必做，否则数据会丢）

机器人的数据（欢迎语、敏感词表、违规记录、发言统计）存在 `/app/data/bot.db` 这个 SQLite 文件里。Railway 的容器文件系统是临时的，**每次重新部署都会清空**，所以必须挂载持久化磁盘：

1. 在项目详情页点服务名（左侧的 `mike` 服务卡片）
2. 进入服务详情后，点 **Volumes**（磁盘）标签
3. 点 **Add Volume**（添加磁盘）：
   - **Mount Path**（挂载路径）填：**`/app/data`**
   - 容量保持默认即可（500MB 免费额度内足够）
4. 保存后服务自动重启，Volume 生效

> 没挂 Volume 的症状：机器人配置/词表/统计在每次部署或重启后全部回到初始状态。

---

## 5. 验证部署是否成功

1. 回到项目首页，点 **Deployments** 标签，看最新一次部署状态：
   - `SUCCESS` = 部署成功
   - `FAILED` = 点进该次部署看日志找原因
2. 点服务卡片 → **Logs**（日志）标签，滚到最后应该能看到：
   ```
   数据库已就绪：data/bot.db
   机器人 @你的机器人用户名 已启动，开始轮询更新…
   ```
3. 打开 Telegram，私聊你的机器人，发 `/start`：
   - 机器人回复"你好！我是群管机器人" → 部署成功 🎉
   - 没反应 → 看下方"常见问题"

---

## 6. 在群里启用（最后一步）

1. 把你的群 **设置 → 添加成员**，搜索机器人用户名，添加进群
2. **把机器人设为群管理员**：群设置 → 管理员 → 添加管理员 → 选机器人 → 权限里勾上：
   - 删除消息
   - 封禁用户
   - 置顶消息
   - 邀请用户（可选）
3. 群里发 `/help`，机器人会回复完整命令手册

> 不设为管理员，入群验证、防广告、敏感词删除、踢人禁言全都无法生效。

---

## 7. 常见问题排查

**Q：部署状态 FAILED / 容器一直重启？**
- 点进该次 Deployment 看日志，常见两种：
  - `未配置 BOT_TOKEN` → 说明 Variables 没填对，回第 3 步检查
  - 依赖安装失败 → 一般网络问题，点 **Redeploy**（重新部署）再试一次

**Q：机器人不回复消息？**
1. 看 Logs 里是否打印了报错（Telegram API 连接异常等）
2. 确认 `BOT_TOKEN` 没复制错（@BotFather 可以 `/mybots` 重新看）
3. 确认服务没被暂停（免费额度用尽会暂停，见下条）

**Q：免费额度用完了？**
- Railway 新用户 $5 试用额度 ≈ 500 小时/月，24/7 常驻约 20 天耗尽
- 额度耗尽服务自动暂停，机器人下线
- 解法：升级付费（Hobby 套餐 $5/月）或改用 Oracle 免费 VPS 长期跑

**Q：以后改了代码怎么更新？**
- 把新代码推送到 GitHub 仓库的 main 分支（`git push` 或重新用上传脚本），Railway 检测到新提交会自动重新部署
- 也可以在 Deployments 里手动点 **Redeploy**

**Q：想关闭某个功能？**
- 群里发 `/captcha off`（关入群验证）、`/antispam off`（关防广告）——管理员可用
- 全局默认值改环境变量后重启

---

## 附：部署流程图

```
登录 Railway ──> 从 GitHub 导入 mike 仓库 ──> 构建部署(自动识别 Dockerfile)
     │                                          │
     │                                          ▼
     └─────────────── 配置 Variables(BOT_TOKEN / ADMIN_IDS) ──> 挂载 Volume(/app/data)
                                                                        │
                                                                        ▼
                                                  群里启用(拉进群+设管理员) <── 日志确认"机器人已启动"
```

遇到任何一步卡住，把截图或报错信息发给我，我帮你排查。
