# 🚀 CDP Agent Skill Pack

**Control any browser on any Windows PC in your LAN from your AI agent.**
Real Chrome, real fingerprints, real automation. No headless. No detection.

[English](#english) | [中文](#chinese)

---

## English

### What is this?

CDP Agent lets your AI agent (Hermes/OpenClaude/OpenClaw) **take over real Chrome browsers** running on Windows machines in your local network. 

Not a headless Chromium. Not a Playwright bot. **Your actual Chrome browser** with all its cookies, login sessions, and human-like fingerprints.

### Why not just use headless Chrome?

| | Headless Chromium | CDP Agent (this) |
|---|---|---|
| Bot detection | ❌ Easily blocked (Cloudflare, captchas) | ✅ Real Chrome, real fingerprints |
| Login sessions | ❌ No cookies, need to auth every time | ✅ Uses your existing Chrome login |
| Anti-detection | ❌ Requires complex setup | ✅ Auto-injected stealth scripts |
| CPU/RAM | ❌ Heavy, runs on server | ✅ Runs on your desktop, zero server load |
| Network | ❌ Server IP gets banned | ✅ Uses your home/office IP |
| Multi-machine | ❌ Single instance | ✅ Control 10+ Windows PCs at once |

### What can you do with it?

- **🤖 AI-powered web testing** — Let your AI agent test your websites on real Chrome
- **📊 Scraping at scale** — Control multiple Windows PCs to scrape without getting blocked
- **💼 Job auto-apply** — BOSS直聘, LinkedIn, 猎聘, any job site — let AI find and apply
- **📈 Marketing automation** — Post on social media, manage ads, monitor competitors
- **🛒 E-commerce ops** — Monitor prices, manage stores, automate orders
- **🔍 OSINT / research** — Browse sites that block headless browsers
- **🧪 QA automation** — Run visual tests on real browsers across machines

### Roadmap — More Platform Skills Coming

The CDP Agent is the **infrastructure layer**. On top of it, we're building platform-specific skills:

| Platform Skill | Status | What it does |
|---------------|--------|-------------|
| **boss-zhipin** | ✅ Done | BOSS直聘 auto-apply — search remote/part-time tech jobs |
| **x-twitter** | 🔜 Planned | X/Twitter — auto-post, search, engage, monitor trends |
| **reddit** | 🔜 Planned | Reddit — auto-post, reply, monitor subreddits, Karma farming |
| **linkedin** | 🔜 Planned | LinkedIn — auto-apply, network, send connection requests |
| **zhihu** | 🔜 Planned | 知乎 — auto-post answers, content farming |
| **xiaohongshu** | 🔜 Planned | 小红书 — auto-post notes, engage |
| **douyin** | 🔜 Planned | 抖音 — auto-post, comment, engage |
| **weibo** | 🔜 Planned | 微博 — auto-post, trend monitoring |
| **taobao** | 🔜 Planned | 淘宝 — price monitoring, store ops |
| **zillow** | 🔜 Planned | Zillow/real estate — property scraping, alerting |
| **more...** | 🔜 TBD | Open to community contributions! |

All platform skills follow the same pattern:
```
skill-name/scripts/run.py --ip WINDOWS_IP --action what_to_do
```

Want a specific platform? Open an issue or contribute a PR.

### Multi-Profile Architecture

```
┌─────────────────────────────────────────────────────┐
│              Hermes / OpenClaude / OpenClaw           │
│  (AI Agent - runs on Linux/Mac/WSL)                  │
│                                                      │
│  Profile 1: Windows PC 192.168.50.229 (Chrome)       │
│  Profile 2: Windows PC 192.168.50.230 (Chrome)       │
│  Profile 3: Windows PC 192.168.50.231 (Edge)         │
│  ... up to N machines                                │
└──────────────┬──────────────┬──────────────┬────────┘
               │              │              │
       WebSocket             WebSocket             WebSocket
               │              │              │
┌──────────────▼──┐ ┌────────▼──────┐ ┌──────▼───────────┐
│ Windows PC #1    │ │ Windows PC #2 │ │ Windows PC #N    │
│ cdp_agent_win.py │ │ cdp_agent_win │ │ cdp_agent_win.py │
│ Chrome Browser   │ │ Chrome/Edge   │ │ Any Browser      │
│ Profile: work    │ │ Profile: home │ │ Profile: test    │
└─────────────────┘ └───────────────┘ └──────────────────┘
```

Each Windows PC runs `cdp_agent_win.py` which:
1. Auto-detects your OS (Windows/Mac/Linux) and browser (Chrome/Edge/Chromium)
2. Auto-starts browser with remote debugging
3. Injects anti-detection scripts into every page
4. Exposes a WebSocket API on port 19400
5. Your AI agent connects and sends commands

### Deployment Modes

**Local mode** (AI agent and browser on same machine):
```python
b = SyncClient("ws://127.0.0.1:19400")
```
No LAN config needed. Works on Windows, Mac, Linux.

**Remote mode** (control another machine):
```python
b = SyncClient("ws://192.168.50.229:19400")
```

**Multi-machine mode**:
```python
pc1 = SyncClient("ws://192.168.50.229:19400")
pc2 = SyncClient("ws://192.168.50.230:19400")
```

### Quick Start

#### 1. Start the middleware (on any OS)

```bash
pip install websockets psutil httpx
python cdp_agent_win.py
```

The middleware auto-detects your OS (Windows/Mac/Linux) and finds Chrome/Edge/Chromium.

Or start your browser manually with remote debugging:
```bash
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\temp\chrome_debug

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --remote-allow-origins=*

# Linux
google-chrome --remote-debugging-port=9222 --remote-allow-origins=*
```

#### 2. Linux (AI Agent - Hermes/OpenClaude/OpenClaw)

```python
from cdp_agent_client import SyncClient

# Control Windows PC #1
pc1 = SyncClient("ws://192.168.50.229:19400")
pc1.navigate("https://www.baidu.com")
print(pc1.eval("document.title"))

# Control Windows PC #2 (same code, different IP)
pc2 = SyncClient("ws://192.168.50.230:19400")
pc2.navigate("https://www.google.com")
```

### 26 Commands Available

| Command | Params | Description |
|---------|--------|-------------|
| ping | - | Health check |
| navigate | url | Open URL |
| click | selector or text | Click element |
| type | selector, text | Type text |
| set_value | selector, value | Set value directly |
| eval | expression | Execute JavaScript |
| screenshot | - | Take screenshot |
| scroll | direction, amount | Scroll page |
| get_page_info | - | Get title + URL |
| get_cookies | - | Get browser cookies |
| highlight | selector | Flash red border |
| ... | ... | 26 total commands |

See [skills/cdp-agent/SKILL.md](skills/cdp-agent/SKILL.md) for the full list.

### Included Skills

| Skill | Description |
|-------|-------------|
| **cdp-agent** | Core browser control library (26 commands) |
| **boss-zhipin** | BOSS直聘 auto-apply — search remote tech jobs, auto-send "立即沟通" |

### Requirements

- Python 3.8+
- Windows PC(s) on the same LAN
- `pip install websockets` (both Linux and Windows)
- `pip install psutil httpx` (Windows only)

---

## Chinese

### 这是什么？

CDP Agent 让你的 AI 助手（Hermes/OpenClaude/OpenClaw）**远程控制局域网内任意 Windows 电脑上的真实 Chrome 浏览器**。

不是无头 Chromium，不是 Playwright 机器人。**是你真实的 Chrome 浏览器**——带着你的 Cookie、登录态、和人一样的浏览器指纹。

### 为什么不用无头浏览器？

| | 无头 Chromium | CDP Agent（本项目） |
|---|---|---|
| 反爬检测 | ❌ 容易被拦截（Cloudflare、验证码） | ✅ 真实 Chrome，真实指纹 |
| 登录态 | ❌ 没 Cookie，每次要重新登录 | ✅ 直接用你 Chrome 已登录的会话 |
| 反检测 | ❌ 需要复杂配置 | ✅ 自动注入反检测脚本 |
| 性能 | ❌ 吃服务器资源 | ✅ 跑在你桌面电脑上，零服务器负载 |
| IP 限制 | ❌ 服务器 IP 容易被封 | ✅ 用你家庭/办公室 IP |
| 多机控制 | ❌ 单实例 | ✅ 同时控制 10+ 台 Windows |

### 能做什么？

- **🤖 AI 自动化测试** — 让 AI 在真实浏览器上测试你的网站
- **📊 大规模采集** — 控制多台 Windows 采集数据，不封 IP
- **💼 自动投简历** — BOSS直聘、猎聘、LinkedIn，AI 帮你找岗投递
- **📈 营销自动化** — 社交媒体发帖、广告管理、竞品监控
- **🛒 电商运营** — 比价监控、店铺管理、自动下单
- **🔍 情报收集** — 浏览那些拦截无头浏览器的网站
- **🧪 QA 自动化** — 跨多台机器的真实浏览器视觉测试

### 路线图 — 更多平台技能即将到来

CDP Agent 是**基础设施层**。基于它，我们会持续开发各平台技能：

| 平台技能 | 状态 | 功能 |
|----------|------|------|
| **boss-zhipin** | ✅ 已完成 | BOSS直聘自动投递 — 搜远程技术岗 |
| **x-twitter** | 🔜 计划中 | X/Twitter — 自动发帖、搜索、互动 |
| **reddit** | 🔜 计划中 | Reddit — 自动发帖、回复、养号 |
| **linkedin** | 🔜 计划中 | LinkedIn — 自动投递、加人脉 |
| **zhihu** | 🔜 计划中 | 知乎 — 自动回答、内容运营 |
| **xiaohongshu** | 🔜 计划中 | 小红书 — 自动发笔记、互动 |
| **douyin** | 🔜 计划中 | 抖音 — 自动发视频、评论 |
| **weibo** | 🔜 计划中 | 微博 — 自动发帖、热搜监控 |
| **taobao** | 🔜 计划中 | 淘宝 — 比价监控、店铺运营 |
| **zillow** | 🔜 计划中 | Zillow/房产 — 房源监控 |
| **更多...** | 🔜 待定 | 欢迎社区贡献！ |

所有平台技能统一格式：
```
skill-name/scripts/run.py --ip WINDOWS_IP --action what_to_do
```

想要某个平台？提 Issue 或贡献 PR。

### 多 Profile 架构

```
┌─────────────────────────────────────────┐
│          AI 助手 (Linux/Mac/WSL)          │
│                                          │
│  Profile 1: Windows 192.168.50.229       │
│  Profile 2: Windows 192.168.50.230       │
│  Profile 3: Windows 192.168.50.231       │
│  ... 想控多少台就控多少台                  │
└──────────┬──────────┬──────────┬────────┘
           │          │          │
    WebSocket     WebSocket     WebSocket
           │          │          │
┌──────────▼──┐ ┌────▼────┐ ┌──▼──────────┐
│ Windows #1  │ │ Win #2  │ │ Windows #N  │
│ 中间件+Chrome│ │ 中间件   │ │ 中间件+Edge │
│ 工作Profile │ │ 家庭    │ │ 测试Profile  │
└─────────────┘ └─────────┘ └─────────────┘
```

每台 Windows 跑 `cdp_agent_win.py`，AI 通过 WebSocket 连接并发控制。

### 部署模式

**本机模式**（AI 和浏览器在同一台电脑）：
```python
b = SyncClient("ws://127.0.0.1:19400")
```
不需要改任何配置，Windows/Mac/Linux 都支持。

**远程模式**（控制局域网另一台电脑）：
```python
b = SyncClient("ws://192.168.50.229:19400")
```

**多机并发模式**：
```python
pc1 = SyncClient("ws://192.168.50.229:19400")
pc2 = SyncClient("ws://192.168.50.230:19400")
```

### 快速开始

#### 1. 启动中间件（支持 Windows/Mac/Linux）

```bash
pip install websockets psutil httpx
python cdp_agent_win.py
```

中间件会自动检测你的操作系统和浏览器。

或者手动启动带远程调试的浏览器：
```bash
# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\temp\chrome_debug

# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --remote-allow-origins=*

# Linux
google-chrome --remote-debugging-port=9222 --remote-allow-origins=*
```

#### 2. Linux（AI 助手）

```python
from cdp_agent_client import SyncClient

# 控制 Windows #1
pc1 = SyncClient("ws://192.168.50.229:19400")
pc1.navigate("https://www.baidu.com")

# 控制 Windows #2（换个 IP 就行）
pc2 = SyncClient("ws://192.168.50.230:19400")
pc2.navigate("https://www.google.com")
```

### 包含的技能

| 技能 | 说明 |
|------|------|
| **cdp-agent** | 浏览器远程控制核心库，26 个命令 |
| **boss-zhipin** | BOSS直聘自动投递 — 搜远程技术岗，自动发"立即沟通" |

### 环境要求

- Python 3.8+
- 局域网内的 Windows 电脑
- `pip install websockets`（Linux 和 Windows 都需要）
- `pip install psutil httpx`（仅 Windows）

---

## Project Structure

```
skills/
├── cdp-agent/              # Core: browser remote control
│   ├── SKILL.md
│   ├── cdp_agent_win.py    # Windows middleware (run this)
│   └── cdp_agent_client.py # Python client lib (import this)
│
└── boss-zhipin/            # BOSS直聘 automation
    ├── SKILL.md
    └── scripts/
        └── run.py          # CLI entry point
```

## License

MIT

## Contact & Support

- **Issues & Feature Requests:** [github.com/linpengishero/cdp-agent-skillpack/issues](https://github.com/linpengishero/cdp-agent-skillpack/issues)
- **Email:** 459082139@qq.com
- **Custom development:** Open an issue or send an email for commercial support, custom skills, or enterprise deployment.
