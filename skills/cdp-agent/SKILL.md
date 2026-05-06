---
name: cdp-agent
description: Control any real browser (Chrome/Edge/Chromium) on any OS (Windows/Mac/Linux) via WebSocket from your AI agent.
version: 3.0.0
---

# CDP Agent — Browser Remote Control

Control a **real browser** on **any machine** from your AI agent. Cross-platform, anti-detection, 26 commands.

## Architecture

Three deployment modes:

### Mode 1: Local (simplest — AI and browser on same machine)

```
Hermes/OpenClaude + cdp_agent_win.py + Chrome
         ↕ ws://127.0.0.1:19400
    All on one Windows/Mac/Linux PC
```

### Mode 2: Remote (control another machine on LAN)

```
AI Agent (Linux/Mac)  ←WebSocket→  Windows/Mac/Linux (middleware + Chrome)
```

### Mode 3: Multi-machine (control many PCs at once)

```
AI Agent ←ws→ PC #1 (Chrome)
         ←ws→ PC #2 (Edge)
         ←ws→ PC #N (Chromium)
```

## Quick Start

```bash
pip install websockets psutil httpx
python cdp_agent_win.py
```

The middleware auto-detects your OS and finds Chrome/Edge/Chromium automatically.

### Platform Support

| OS | Auto-detect | Tested |
|----|-------------|--------|
| Windows | ✅ Chrome, Edge, Chromium | ✅ |
| macOS | ✅ Google Chrome, Chromium, Edge | ✅ |
| Linux | ✅ google-chrome, chromium, chromium-browser, Edge | ✅ |

Override with environment variable:
```bash
export CHROME_PATH=/custom/path/to/browser
python cdp_agent_win.py
```

## Client Usage

```python
import sys
sys.path.insert(0, '/path/to/skills/cdp-agent')
from cdp_agent_client import SyncClient

# Local: use 127.0.0.1
b = SyncClient("ws://127.0.0.1:19400")

# Remote: use LAN IP
# b = SyncClient("ws://192.168.50.229:19400")

b.navigate("https://www.baidu.com")
print(b.eval("document.title"))
```

## Commands

| Command | Params | Description |
|---------|--------|-------------|
| ping | - | Health check |
| navigate | url | Open URL |
| click | selector or text | Click element |
| type | selector, text | Type text |
| set_value | selector, value | Set input value directly |
| eval | expression | Execute JS, return value |
| screenshot | - | Screenshot (JPEG base64) |
| snapshot | - | Page text snapshot |
| scroll | direction, amount | Scroll page |
| scroll_to | selector | Scroll to element |
| get_page_info | - | Get {title, url} |
| get_html | - | Get full HTML |
| get_text | - | Get visible text |
| get_attributes | selector | Get element attributes |
| get_cookies | - | Get cookies |
| clear_cookies | - | Clear cookies |
| highlight | selector | Highlight element (red border) |
| hover | selector | Mouse hover |
| reload | ignore_cache | Reload page |
| go_back | - | Browser back |
| go_forward | - | Browser forward |
| key_press | key | Send key (Enter/Tab/Arrow) |
| wait_for | selector, timeout | Wait for element |
| new_tab | - | Create new tab |
| close_tab | - | Close current tab |
| restart_chrome | - | Restart Chrome |

## Notes

- click uses CDP mouse events. Some buttons may not trigger submission. Use `eval` with JS click as fallback.
- screenshot returns JPEG base64. Decode with `base64.b64decode()`.
- eval returns raw JS value. eval_json auto-parses JSON strings.
- For local mode: connect to `ws://127.0.0.1:19400` (no network config needed)
- For multi-machine: each machine needs its own `cdp_agent_win.py` running
