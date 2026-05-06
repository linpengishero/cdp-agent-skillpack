"""
CDP Agent — Windows Chrome Remote Control Agent
================================================

Runs on a Windows machine, controls Chrome via CDP, and exposes
a WebSocket interface (port 19400) for remote clients.

Features:
- Auto-starts Chrome with --remote-debugging-port
- Injects anti-detection scripts into every new tab
- Handles WebSocket disconnections gracefully
- Supports 20+ browser automation commands

Requirements: Python 3.8+, pip install websockets psutil httpx

Usage:
    python cdp_agent_win.py

Then connect from another machine:
    ws://<this_ip>:19400

Author: github.com/yourname/cdp-agent
License: MIT
"""

import asyncio
import json
import os
import sys
import subprocess
import time
import logging
import tempfile
from datetime import datetime

# Auto-install missing dependencies
for pkg, import_name in [("websockets", "websockets"), ("psutil", "psutil"), ("httpx", "httpx")]:
    try:
        __import__(import_name)
    except ImportError:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

import websockets
import psutil
import httpx

# ============================================================
# Configuration
# ============================================================

WS_HOST = "0.0.0.0"
WS_PORT = 19400
CHROME_PORT = 9222
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = os.path.join(tempfile.gettempdir(), "chrome_cdp_agent")

# Anti-detection script injected into every new page
STEALTH_SCRIPT = """
// ============================================================
// Anti-detection — injected into every new page before any JS runs
// ============================================================

// 1. Hide automation flags
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. Mock plugins (length probes)
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});
Object.defineProperty(navigator, 'mimeTypes', {
    get: () => [1, 2, 3, 4],
});

// 3. Language & locale
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
Object.defineProperty(navigator, 'language', { get: () => 'zh-CN' });

// 4. Hardware profile (consistent with a normal Win10 PC)
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });

// 5. Chrome runtime object
if (!window.chrome) {
    Object.defineProperty(window, 'chrome', {
        get: () => ({
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: { isInstalled: false },
        }),
    });
}

// 6. WebGL vendor (spoof to common Real GPU instead of SwiftShader)
try {
    const getParam = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        if (param === 37445) return 'Google Inc. (Intel)';  // UNMASKED_VENDOR_WEBGL
        if (param === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
        return getParam.call(this, param);
    };
} catch(e) {}

// 7. Hide CDP connection traces
// Some sites check for $cdp / $chrome_devtools / __webdriver_script_fn
for (const key of ['$cdp', '$chrome_debug', '__webdriver_script_fn', '$cdp_obj']) {
    try { Object.defineProperty(window, key, { get: () => undefined }); } catch(e) {}
}

// 8. Override Function.prototype.toString to hide native code traces
// (sites that check 'function () { [native code] }' patterns)
try {
    const origToString = Function.prototype.toString;
    Function.prototype.toString = function() {
        if (this === window.chrome.runtime.connect) return 'function connect() { [native code] }';
        if (this === navigator.webdriver) return 'function webdriver() { [native code] }';
        return origToString.call(this);
    };
} catch(e) {}

// 9. Permission queries bypass
if (navigator.permissions && navigator.permissions.query) {
    const orig = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = (p) =>
        p.name === 'notifications'
            ? Promise.resolve({ state: 'denied' })
            : orig(p);
}

// 10. Screen & viewport (consistent)
try {
    Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
    Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
} catch(e) {}
"""

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cdp-agent")


# ============================================================
# Chrome Manager
# ============================================================

class ChromeManager:
    """Manages Chrome process lifecycle."""

    def __init__(self):
        self.process = None

    def is_listening(self) -> bool:
        """Check if Chrome is listening on the debug port."""
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.settimeout(1)
            s.connect(("127.0.0.1", CHROME_PORT))
            s.close()
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def start(self) -> bool:
        """Launch Chrome with remote debugging enabled."""
        if self.is_listening():
            logger.info(f"Chrome already listening on 127.0.0.1:{CHROME_PORT}")
            return True

        logger.info("Starting Chrome (remote debugging mode)...")
        os.makedirs(USER_DATA_DIR, exist_ok=True)

        try:
            self.process = subprocess.Popen(
                [
                    CHROME_PATH,
                    f"--remote-debugging-port={CHROME_PORT}",
                    "--remote-allow-origins=*",
                    f"--user-data-dir={USER_DATA_DIR}",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(15):
                if self.is_listening():
                    logger.info(f"Chrome started (PID: {self.process.pid})")
                    return True
                time.sleep(1)
            logger.error("Chrome start timeout")
            return False
        except FileNotFoundError:
            logger.error(f"Chrome not found at: {CHROME_PATH}")
            logger.info("Update CHROME_PATH in the script to your Chrome executable path.")
            return False

    def ensure_running(self) -> bool:
        """Ensure Chrome is running, start if needed."""
        return True if self.is_listening() else self.start()

    def stop(self):
        """Stop Chrome."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            self.process = None


# ============================================================
# CDP Session
# ============================================================

class CDPSession:
    """Persistent Chrome DevTools Protocol session."""

    def __init__(self):
        self.ws = None
        self._msg_id = 0
        self._pending = {}
        self._recv_task = None
        self._running = False

    async def connect(self):
        """Connect to Chrome CDP WebSocket."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"http://127.0.0.1:{CHROME_PORT}/json/version",
                timeout=5,
            )
            data = resp.json()
            ws_url = data["webSocketDebuggerUrl"]

        self.ws = await asyncio.wait_for(
            websockets.connect(ws_url, max_size=None, ping_interval=None),
            timeout=10,
        )
        self._running = True
        self._recv_task = asyncio.create_task(self._recv_loop())
        logger.info("Connected to Chrome CDP")

    async def _recv_loop(self):
        """Receive CDP messages and route to pending futures."""
        try:
            while self._running:
                raw = await self.ws.recv()
                msg = json.loads(raw)
                msg_id = msg.get("id")
                if msg_id and msg_id in self._pending:
                    future = self._pending.pop(msg_id)
                    if not future.done():
                        if "error" in msg:
                            future.set_exception(
                                RuntimeError(json.dumps(msg["error"], ensure_ascii=False))
                            )
                        else:
                            future.set_result(msg["result"])
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Recv error: {e}")
            self._running = False
            for f in self._pending.values():
                if not f.done():
                    f.set_exception(RuntimeError(f"Connection lost: {e}"))
            self._pending.clear()

    async def send(self, method, params=None, session_id=None, timeout=30):
        """Send a CDP command and wait for the response."""
        if not self._running or not self.ws:
            raise RuntimeError("Not connected to CDP")

        self._msg_id += 1
        req = {"id": self._msg_id, "method": method, "params": params or {}}
        if session_id:
            req["sessionId"] = session_id

        future = asyncio.get_event_loop().create_future()
        self._pending[self._msg_id] = future
        await self.ws.send(json.dumps(req))

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(self._msg_id, None)
            raise TimeoutError(f"CDP {method} timed out")

    async def create_tab(self):
        """Create a new tab and inject anti-detection script."""
        r = await self.send("Target.createTarget", {
            "url": "about:blank", "newWindow": False,
        })
        target_id = r["targetId"]
        r = await self.send("Target.attachToTarget", {
            "targetId": target_id, "flatten": True,
        })
        session_id = r["sessionId"]
        await self.send("Page.addScriptToEvaluateOnNewDocument", {
            "source": STEALTH_SCRIPT,
        }, session_id=session_id)
        return {"targetId": target_id, "sessionId": session_id}

    async def close(self):
        """Close the CDP connection."""
        self._running = False
        if self._recv_task:
            self._recv_task.cancel()
        if self.ws:
            await self.ws.close()


# ============================================================
# Command Handlers
# ============================================================

class CDPAgent:
    """WebSocket server that receives commands and drives Chrome via CDP."""

    def __init__(self):
        self.cdp = CDPSession()
        self.chrome = ChromeManager()
        self.active_tab = None

    async def start(self):
        """Start the agent — ensure Chrome, connect CDP, serve WebSocket."""
        if not self.chrome.ensure_running():
            logger.error("Failed to start Chrome, exiting.")
            return

        try:
            await self.cdp.connect()
        except Exception as e:
            logger.error(f"Failed to connect CDP: {e}")
            return

        logger.info(f"WebSocket server: ws://0.0.0.0:{WS_PORT}")
        async with websockets.serve(
            self.handle_client, WS_HOST, WS_PORT,
            ping_interval=30, ping_timeout=10,
        ):
            await asyncio.Future()

    async def ensure_tab(self):
        if not self.active_tab:
            self.active_tab = await self.cdp.create_tab()
        return self.active_tab

    # ---- Message handling ----

    async def handle_client(self, websocket):
        logger.info(f"Client connected: {websocket.remote_address}")
        try:
            async for message in websocket:
                try:
                    result = await self.handle_command(message)
                    await websocket.send(json.dumps(result, ensure_ascii=False))
                except Exception as e:
                    await websocket.send(json.dumps({
                        "error": f"{type(e).__name__}: {str(e)}",
                        "success": False,
                    }))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            logger.info(f"Client disconnected: {websocket.remote_address}")

    async def handle_command(self, message):
        try:
            cmd = json.loads(message)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON", "success": False}

        action = cmd.get("action", "")
        params = cmd.get("params", {})

        handlers = {
            "ping": self._cmd_ping,
            "navigate": self._cmd_navigate,
            "click": self._cmd_click,
            "type": self._cmd_type,
            "eval": self._cmd_eval,
            "screenshot": self._cmd_screenshot,
            "snapshot": self._cmd_snapshot,
            "scroll": self._cmd_scroll,
            "new_tab": self._cmd_new_tab,
            "close_tab": self._cmd_close_tab,
            "get_page_info": self._cmd_get_page_info,
            "restart_chrome": self._cmd_restart_chrome,
            "get_html": self._cmd_get_html,
            "get_text": self._cmd_get_text,
            "get_cookies": self._cmd_get_cookies,
            "clear_cookies": self._cmd_clear_cookies,
            "highlight": self._cmd_highlight,
            "hover": self._cmd_hover,
            "reload": self._cmd_reload,
            "go_back": self._cmd_go_back,
            "go_forward": self._cmd_go_forward,
            "wait_for": self._cmd_wait_for,
            "scroll_to": self._cmd_scroll_to,
            "get_attributes": self._cmd_get_attributes,
            "set_value": self._cmd_set_value,
            "key_press": self._cmd_key_press,
        }

        handler = handlers.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}", "success": False}

        try:
            return await handler(params)
        except Exception as e:
            logger.error(f"Command '{action}' failed: {e}")
            return {"error": str(e), "success": False}

    # ---- Internal helpers ----

    async def _eval(self, expr):
        """Quick internal JS eval (silent on failure)."""
        if not self.active_tab:
            return ""
        try:
            r = await self.cdp.send("Runtime.evaluate", {
                "expression": expr,
                "awaitPromise": True,
                "returnByValue": True,
            }, session_id=self.active_tab["sessionId"])
            return r.get("result", {}).get("value", "")
        except Exception:
            return ""

    async def _click_at(self, tab, x, y):
        """Simulate a human-like mouse click at coordinates.

        Includes random mouse movement, variable hold time, and
        randomized delays to avoid bot detection.
        """
        import random as _r

        # Random offset: humans never click dead center
        jitter = lambda: _r.uniform(-3, 3)
        cx, cy = x + jitter(), y + jitter()

        # Phase 1: Move mouse to a random nearby point first
        approach_x = cx + _r.uniform(-50, 50)
        approach_y = cy + _r.uniform(-50, 50)
        await self.cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseMoved", "x": approach_x, "y": approach_y,
        }, session_id=tab["sessionId"])
        await asyncio.sleep(_r.uniform(0.05, 0.15))

        # Phase 2: Move to the target with a small curve
        steps = _r.randint(3, 6)
        for i in range(1, steps + 1):
            t = i / steps
            mx = approach_x + (cx - approach_x) * t + _r.uniform(-2, 2)
            my = approach_y + (cy - approach_y) * t + _r.uniform(-2, 2)
            await self.cdp.send("Input.dispatchMouseEvent", {
                "type": "mouseMoved", "x": mx, "y": my,
            }, session_id=tab["sessionId"])
            await asyncio.sleep(_r.uniform(0.01, 0.03))

        # Phase 3: Mouse over
        await asyncio.sleep(_r.uniform(0.02, 0.08))
        await self.cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseMoved", "x": cx, "y": cy,
        }, session_id=tab["sessionId"])
        await asyncio.sleep(_r.uniform(0.03, 0.1))

        # Phase 4: Press (human hold: 50-200ms)
        await self.cdp.send("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": cx, "y": cy,
            "button": "left", "clickCount": 1,
        }, session_id=tab["sessionId"])
        await asyncio.sleep(_r.uniform(0.05, 0.2))

        # Phase 5: Release
        await self.cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": cx, "y": cy,
            "button": "left", "clickCount": 1,
        }, session_id=tab["sessionId"])

        # Phase 6: Tiny post-click pause (human reaction)
        await asyncio.sleep(_r.uniform(0.05, 0.15))

    async def _find_element_rect(self, tab, selector=None, text=None):
        """Find element by CSS selector or text, return {x, y, tag, text}."""
        if selector:
            expr = f"""
                (()=>{{const el=document.querySelector({json.dumps(selector)});
                if(!el)return{{found:false}};
                const r=el.getBoundingClientRect();el.scrollIntoView({{block:'center'}});
                await new Promise(r=>setTimeout(r,300));
                const r2=el.getBoundingClientRect();
                return{{found:true,x:r2.left+r2.width/2,y:r2.top+r2.height/2,tag:el.tagName}};}})()
            """
        elif text:
            expr = f"""
                (()=>{{const t={json.dumps(text)};
                const all=[...document.querySelectorAll('a,button,input[type=submit],input[type=button],[role=button],[onclick]')];
                let best=null,bestScore=0;
                for(const el of all){{
                    const txt=(el.innerText||el.value||el.textContent||'').trim();
                    if(txt===t){{best=el;break;}}
                    if(txt.includes(t)&&txt.length>bestScore){{best=el;bestScore=txt.length;}}
                }}
                if(!best)return{{found:false}};
                const r=best.getBoundingClientRect();best.scrollIntoView({{block:'center'}});
                await new Promise(r=>setTimeout(r,300));
                const r2=best.getBoundingClientRect();
                return{{found:true,x:r2.left+r2.width/2,y:r2.top+r2.height/2,tag:best.tagName,text:(best.innerText||best.value||'').substring(0,30)}};}})()
            """
        else:
            raise ValueError("Provide selector or text")

        r = await self.cdp.send("Runtime.evaluate", {
            "expression": expr, "awaitPromise": True,
        }, session_id=tab["sessionId"])
        return r.get("result", {}).get("value", {})

    # ---- Command implementations ----

    async def _cmd_ping(self, params):
        return {"success": True, "pong": True, "chrome_running": self.chrome.is_listening()}

    async def _cmd_navigate(self, params):
        tab = await self.ensure_tab()
        url = params.get("url", "")
        if not url:
            return {"error": "url is required", "success": False}
        await self.cdp.send("Page.navigate", {"url": url}, session_id=tab["sessionId"])
        await asyncio.sleep(1)
        title = await self._eval("document.title")
        return {"success": True, "url": url, "title": title}

    async def _cmd_click(self, params):
        tab = await self.ensure_tab()
        selector = params.get("selector", "")
        text = params.get("text", "")

        if not selector and not text:
            return {"error": "Provide 'selector' (CSS) or 'text' (visible text)", "success": False}

        pos = await self._find_element_rect(tab, selector=selector or None, text=text or None)
        if not pos.get("found"):
            target = f"selector='{selector}'" if selector else f"text='{text}'"
            return {"error": f"Element not found: {target}", "success": False}

        await self._click_at(tab, pos["x"], pos["y"])
        return {"success": True, "element": pos.get("tag", ""), "text": pos.get("text", ""), "x": pos["x"], "y": pos["y"]}

    async def _cmd_type(self, params):
        tab = await self.ensure_tab()
        selector = params.get("selector", "")
        text = params.get("text", "")
        clear = params.get("clear_first", True)

        if not selector:
            return {"error": "selector is required", "success": False}

        await self.cdp.send("Runtime.evaluate", {
            "expression": f"""
                (()=>{{const el=document.querySelector({json.dumps(selector)});
                if(!el)return false;
                el.focus();el.click();
                if({json.dumps(clear)}){{el.value='';el.select();}}
                return true;}})()
            """,
            "awaitPromise": True,
        }, session_id=tab["sessionId"])
        import random as _r
        await asyncio.sleep(_r.uniform(0.1, 0.3))

        for ch in text:
            await self.cdp.send("Input.dispatchKeyEvent", {
                "type": "keyDown", "key": ch, "text": ch,
            }, session_id=tab["sessionId"])
            await asyncio.sleep(_r.uniform(0.03, 0.08))  # human typing interval
            await self.cdp.send("Input.dispatchKeyEvent", {
                "type": "keyUp", "key": ch,
            }, session_id=tab["sessionId"])
            await asyncio.sleep(_r.uniform(0.01, 0.03))

        return {"success": True, "typed": text, "chars": len(text)}

    async def _cmd_eval(self, params):
        tab = await self.ensure_tab()
        expr = params.get("expression", "")
        if not expr:
            return {"error": "expression is required", "success": False}
        r = await self.cdp.send("Runtime.evaluate", {
            "expression": expr, "awaitPromise": True, "returnByValue": True,
        }, session_id=tab["sessionId"])
        val = r.get("result", {})
        return {"success": True, "type": val.get("type"), "value": val.get("value")}

    async def _cmd_screenshot(self, params):
        tab = await self.ensure_tab()
        r = await self.cdp.send("Page.captureScreenshot", {
            "format": "jpeg", "quality": 70,
        }, session_id=tab["sessionId"])
        return {"success": True, "format": "jpeg", "data": r.get("data", "")}

    async def _cmd_snapshot(self, params):
        tab = await self.ensure_tab()
        try:
            r = await self.cdp.send("Accessibility.getFullAXTree", {}, session_id=tab["sessionId"])
            lines = []
            for n in r.get("nodes", []):
                name = ""
                for p in n.get("properties", []):
                    if p.get("name") == "name":
                        name = p.get("value", {}).get("value", "")
                if name:
                    lines.append(f"[{n.get('role',{}).get('value','')}] {name}")
            return {"success": True, "snapshot": "\n".join(lines[:200])}
        except Exception:
            text = await self._eval("document.body?.innerText?.substring(0,3000)||''")
            return {"success": True, "snapshot": text, "note": "DOM fallback"}

    async def _cmd_scroll(self, params):
        tab = await self.ensure_tab()
        direction = params.get("direction", "down")
        amount = params.get("amount", 500)
        delta = amount if direction == "down" else -amount
        await self.cdp.send("Runtime.evaluate", {
            "expression": f"window.scrollBy({{top:{delta},left:0,behavior:'smooth'}})",
        }, session_id=tab["sessionId"])
        return {"success": True}

    async def _cmd_new_tab(self, params):
        self.active_tab = await self.cdp.create_tab()
        return {"success": True}

    async def _cmd_close_tab(self, params):
        if self.active_tab:
            try:
                await self.cdp.send("Target.closeTarget", {
                    "targetId": self.active_tab["targetId"],
                })
            except Exception:
                pass
            self.active_tab = None
        return {"success": True}

    async def _cmd_get_page_info(self, params):
        title = await self._eval("document.title")
        url = await self._eval("document.location.href")
        return {"success": True, "title": title, "url": url}

    async def _cmd_restart_chrome(self, params):
        await self._cmd_close_tab(params)
        await self.cdp.close()
        self.chrome.stop()
        time.sleep(2)
        if self.chrome.start():
            await self.cdp.connect()
            return {"success": True}
        return {"error": "Failed to restart Chrome", "success": False}

    async def _cmd_get_html(self, params):
        tab = await self.ensure_tab()
        r = await self.cdp.send("Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True,
        }, session_id=tab["sessionId"])
        html = r.get("result", {}).get("value", "")
        return {"success": True, "html": html[:50000]}

    async def _cmd_get_text(self, params):
        tab = await self.ensure_tab()
        expr = params.get("expression", "document.body?.innerText || ''")
        r = await self.cdp.send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
        }, session_id=tab["sessionId"])
        text = r.get("result", {}).get("value", "")
        return {"success": True, "text": str(text)[:10000]}

    async def _cmd_get_cookies(self, params):
        r = await self.cdp.send("Network.getAllCookies")
        cookies = r.get("cookies", [])
        return {"success": True, "cookies": cookies}

    async def _cmd_clear_cookies(self, params):
        await self.cdp.send("Network.clearBrowserCookies")
        return {"success": True}

    async def _cmd_highlight(self, params):
        tab = await self.ensure_tab()
        selector = params.get("selector", "")
        if not selector:
            return {"error": "selector is required", "success": False}
        await self.cdp.send("Runtime.evaluate", {
            "expression": f"""
                (()=>{{const el=document.querySelector({json.dumps(selector)});
                if(!el)return false;
                el.style.outline='3px solid red';el.style.outlineOffset='2px';
                setTimeout(()=>{{el.style.outline='';el.style.outlineOffset='';}},3000);
                el.scrollIntoView({{block:'center',behavior:'smooth'}});
                return true;}})()
            """,
        }, session_id=tab["sessionId"])
        return {"success": True}

    async def _cmd_hover(self, params):
        tab = await self.ensure_tab()
        selector = params.get("selector", "")
        if not selector:
            return {"error": "selector is required", "success": False}
        pos = await self._find_element_rect(tab, selector=selector)
        if not pos.get("found"):
            return {"error": f"Element not found: {selector}", "success": False}
        await self.cdp.send("Input.dispatchMouseEvent", {
            "type": "mouseMoved", "x": pos["x"], "y": pos["y"],
        }, session_id=tab["sessionId"])
        return {"success": True}

    async def _cmd_reload(self, params):
        tab = await self.ensure_tab()
        ignore_cache = params.get("ignore_cache", False)
        await self.cdp.send("Page.reload", {"ignoreCache": ignore_cache}, session_id=tab["sessionId"])
        await asyncio.sleep(1)
        return {"success": True}

    async def _cmd_go_back(self, params):
        tab = await self.ensure_tab()
        await self.cdp.send("Runtime.evaluate", {
            "expression": "window.history.back()",
        }, session_id=tab["sessionId"])
        await asyncio.sleep(1)
        title = await self._eval("document.title")
        return {"success": True, "title": title}

    async def _cmd_go_forward(self, params):
        tab = await self.ensure_tab()
        await self.cdp.send("Runtime.evaluate", {
            "expression": "window.history.forward()",
        }, session_id=tab["sessionId"])
        await asyncio.sleep(1)
        title = await self._eval("document.title")
        return {"success": True, "title": title}

    async def _cmd_wait_for(self, params):
        tab = await self.ensure_tab()
        selector = params.get("selector", "")
        timeout = params.get("timeout", 10)
        if not selector:
            return {"error": "selector is required", "success": False}
        for i in range(int(timeout * 2)):
            r = await self.cdp.send("Runtime.evaluate", {
                "expression": f"!!document.querySelector({json.dumps(selector)})",
            }, session_id=tab["sessionId"])
            if r.get("result", {}).get("value"):
                return {"success": True, "waited": i * 0.5}
            await asyncio.sleep(0.5)
        return {"error": f"Timeout waiting for: {selector}", "success": False}

    async def _cmd_scroll_to(self, params):
        tab = await self.ensure_tab()
        selector = params.get("selector", "")
        if not selector:
            return {"error": "selector is required", "success": False}
        await self.cdp.send("Runtime.evaluate", {
            "expression": f"""
                (()=>{{const el=document.querySelector({json.dumps(selector)});
                if(!el)return false;
                el.scrollIntoView({{behavior:'smooth',block:'center'}});
                return true;}})()
            """,
        }, session_id=tab["sessionId"])
        return {"success": True}

    async def _cmd_get_attributes(self, params):
        tab = await self.ensure_tab()
        selector = params.get("selector", "")
        if not selector:
            return {"error": "selector is required", "success": False}
        r = await self.cdp.send("Runtime.evaluate", {
            "expression": f"""
                (()=>{{const el=document.querySelector({json.dumps(selector)});
                if(!el)return{{}};
                const attrs={{}};
                for(const a of el.attributes) attrs[a.name]=a.value;
                attrs._tag=el.tagName;
                attrs._text=(el.innerText||'').substring(0,100);
                attrs._html=el.outerHTML.substring(0,500);
                return attrs;}})()
            """,
            "returnByValue": True,
        }, session_id=tab["sessionId"])
        attrs = r.get("result", {}).get("value", {})
        return {"success": True, "attributes": attrs}

    async def _cmd_set_value(self, params):
        tab = await self.ensure_tab()
        selector = params.get("selector", "")
        value = params.get("value", "")
        if not selector:
            return {"error": "selector is required", "success": False}
        await self.cdp.send("Runtime.evaluate", {
            "expression": f"""
                (()=>{{const el=document.querySelector({json.dumps(selector)});
                if(!el)return false;
                el.value={json.dumps(value)};
                el.dispatchEvent(new Event('input',{{bubbles:true}}));
                el.dispatchEvent(new Event('change',{{bubbles:true}}));
                return true;}})()
            """,
        }, session_id=tab["sessionId"])
        return {"success": True}

    async def _cmd_key_press(self, params):
        tab = await self.ensure_tab()
        key = params.get("key", "Enter")
        vk_map = {"Enter": 13, "Tab": 9, "Escape": 27,
                  "ArrowDown": 40, "ArrowUp": 38, "ArrowLeft": 37, "ArrowRight": 39}
        await self.cdp.send("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": key,
            "windowsVirtualKeyCode": vk_map.get(key, 0),
        }, session_id=tab["sessionId"])
        await asyncio.sleep(0.05)
        await self.cdp.send("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": key,
        }, session_id=tab["sessionId"])
        return {"success": True, "key": key}


# ============================================================
# Entry Point
# ============================================================

def main():
    COMMANDS = [
        ("ping", "Health check"),
        ("navigate", "Open URL"),
        ("click", "Click element (CSS selector or text match)"),
        ("type", "Type text into input field"),
        ("eval", "Execute JavaScript"),
        ("screenshot", "Take screenshot (returns PNG base64)"),
        ("snapshot", "Get page accessibility tree"),
        ("scroll", "Scroll page"),
        ("get_page_info", "Get title + URL"),
        ("get_html", "Get full page HTML"),
        ("get_text", "Get visible text"),
        ("get_cookies", "Get all cookies"),
        ("clear_cookies", "Clear browser cookies"),
        ("highlight", "Flash red border on element"),
        ("hover", "Hover mouse over element"),
        ("reload", "Reload page"),
        ("go_back", "Browser back"),
        ("go_forward", "Browser forward"),
        ("wait_for", "Wait for element to appear"),
        ("scroll_to", "Scroll to element"),
        ("get_attributes", "Get element attributes"),
        ("set_value", "Set input value directly"),
        ("key_press", "Send keyboard key (Enter/Tab/etc.)"),
        ("new_tab", "Create new tab"),
        ("close_tab", "Close current tab"),
        ("restart_chrome", "Restart Chrome"),
    ]

    print("=" * 60)
    print("  CDP Agent — Windows Chrome Remote Control")
    print("=" * 60)
    print()
    print(f"  WebSocket: ws://{WS_HOST}:{WS_PORT}")
    print(f"  Chrome debug port: {CHROME_PORT}")
    print(f"  User data: {USER_DATA_DIR}")
    print()
    print("  Commands:")
    for cmd, desc in COMMANDS:
        print(f"    {cmd:22s} {desc}")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    print()

    agent = CDPAgent()
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        print("\nShutting down...")
        if agent.cdp:
            asyncio.run(agent.cdp.close())
        agent.chrome.stop()
        print("Stopped.")


if __name__ == "__main__":
    main()
