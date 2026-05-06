---
name: cdp-agent
description: Control a real Chrome browser on Windows via WebSocket. Auto-starts Chrome, injects anti-detection scripts.
version: 2.1.0
---

# CDP Agent — Browser Remote Control

Control a real Chrome browser on your Windows PC from Hermes/OpenClaude via WebSocket.

## Architecture

```
Windows: cdp_agent_win.py (middleware) → starts Chrome → WebSocket server (:19400)
Linux:   cdp_agent_client.py (client lib) → connects to WebSocket → sends commands
```

## Prerequisites

On Windows:
```cmd
pip install websockets psutil httpx
python cdp_agent_win.py
```

Or start Chrome manually:
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\temp\chrome_debug
```

## Client Usage

```python
import sys
sys.path.insert(0, '/path/to/skills/cdp-agent')
from cdp_agent_client import SyncClient

b = SyncClient("ws://192.168.50.229:19400")
```

## Commands

| Command | Params | Description |
|---------|--------|-------------|
| ping | - | Health check |
| navigate | url | Open URL |
| click | selector or text | Click element (CSS selector or text) |
| type | selector, text, clear_first | Type text (keyboard emulation) |
| set_value | selector, value | Set input value directly |
| eval | expression | Execute JS, return value |
| screenshot | - | Screenshot (base64) |
| snapshot | - | Page text snapshot |
| scroll | direction, amount | Scroll page |
| scroll_to | selector | Scroll to element |
| get_page_info | - | Get {title, url} |
| get_html | - | Get full HTML |
| get_text | - | Get visible text |
| get_attributes | selector | Get element attributes |
| get_cookies | - | Get cookies |
| clear_cookies | - | Clear cookies |
| highlight | selector | Highlight element |
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
- Requires Windows PC on the same LAN as the Hermes/OpenClaude host.
