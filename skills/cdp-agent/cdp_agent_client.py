"""
CDP Agent Client
=================

Async & sync WebSocket client for cdp-agent-win (Windows Chrome automation agent).

Usage:
    import asyncio
    from cdp_agent_client import CDPClient

    async def main():
        b = CDPClient("ws://192.168.50.229:19400")
        await b.navigate("https://www.baidu.com")
        title = await b.eval("document.title")
        print(title)
        await b.close()

    asyncio.run(main())

Or sync version (for execute_code / Jupyter):
    from cdp_agent_client import SyncClient
    b = SyncClient("ws://192.168.50.229:19400")
    b.navigate("https://www.baidu.com")
    print(b.eval("document.title"))

Commands supported:
    ping, navigate, click, type, eval, screenshot, snapshot, scroll,
    new_tab, close_tab, get_page_info, restart_chrome,
    get_html, get_text, get_cookies, clear_cookies,
    highlight, hover, reload, go_back, go_forward,
    wait_for, scroll_to, get_attributes, set_value, key_press
"""

import json
import base64
import time
from typing import Optional, Union, Any

try:
    import websockets
    import asyncio
except ImportError:
    raise ImportError("cdp_agent_client requires 'websockets': pip install websockets")


class CDPClient:
    """Async WebSocket client for cdp-agent-win.

    Each method sends a command and waits for the response.
    Connection is lazy — first command triggers connect.
    """

    def __init__(self, ws_url: str = "ws://192.168.50.229:19400", timeout: float = 30):
        self.ws_url = ws_url
        self.timeout = timeout
        self._ws = None

    # ---- Internal ----

    async def _connect(self):
        if not self._ws:
            self._ws = await asyncio.wait_for(
                websockets.connect(self.ws_url, ping_interval=30, ping_timeout=10),
                timeout=10,
            )
        return self._ws

    async def _send(self, action: str, params: dict = None) -> dict:
        ws = await self._connect()
        msg = json.dumps({"action": action, "params": params or {}})
        await ws.send(msg)
        resp = await asyncio.wait_for(ws.recv(), timeout=self.timeout)
        return json.loads(resp)

    # ---- Connection ----

    async def ping(self) -> bool:
        """Health check. Returns True if agent is reachable."""
        try:
            r = await self._send("ping")
            return r.get("success") and r.get("pong", False)
        except Exception:
            return False

    async def close(self):
        """Close WebSocket connection."""
        if self._ws:
            await self._ws.close()
            self._ws = None

    # ---- Navigation ----

    async def navigate(self, url: str) -> dict:
        """Open a URL in the browser. Returns {success, url, title}."""
        return await self._send("navigate", {"url": url})

    async def new_tab(self) -> dict:
        """Create a new tab."""
        return await self._send("new_tab")

    async def close_tab(self) -> dict:
        """Close the current tab."""
        return await self._send("close_tab")

    async def reload(self, ignore_cache: bool = False) -> dict:
        """Reload the current page."""
        return await self._send("reload", {"ignore_cache": ignore_cache})

    async def go_back(self) -> dict:
        """Go back in browser history."""
        return await self._send("go_back")

    async def go_forward(self) -> dict:
        """Go forward in browser history."""
        return await self._send("go_forward")

    # ---- Element interaction ----

    async def click(self, selector: str = None, text: str = None) -> dict:
        """Click an element by CSS selector or visible text.

        Args:
            selector: CSS selector (e.g. '#kw', '.s_btn')
            text: Visible text content (e.g. '搜索', 'Submit')
        """
        params = {}
        if selector:
            params["selector"] = selector
        if text:
            params["text"] = text
        return await self._send("click", params)

    async def type(self, selector: str, text: str, clear_first: bool = True) -> dict:
        """Type text into an input field (real keyboard emulation).

        Args:
            selector: CSS selector for the input element
            text: Text to type
            clear_first: Clear the field before typing
        """
        return await self._send("type", {
            "selector": selector,
            "text": text,
            "clear_first": clear_first,
        })

    async def set_value(self, selector: str, value: str) -> dict:
        """Set an input field's value directly (fast, no key emulation).

        Dispatches input + change events so JS listeners still fire.
        """
        return await self._send("set_value", {"selector": selector, "value": value})

    async def key_press(self, key: str = "Enter") -> dict:
        """Send a keyboard key event.

        Common keys: Enter, Tab, Escape, ArrowDown, ArrowUp
        """
        return await self._send("key_press", {"key": key})

    async def hover(self, selector: str) -> dict:
        """Hover mouse over an element."""
        return await self._send("hover", {"selector": selector})

    async def scroll(self, direction: str = "down", amount: int = 500) -> dict:
        """Scroll the page.

        Args:
            direction: 'down' or 'up'
            amount: Pixels to scroll
        """
        return await self._send("scroll", {"direction": direction, "amount": amount})

    async def scroll_to(self, selector: str) -> dict:
        """Scroll until an element is visible."""
        return await self._send("scroll_to", {"selector": selector})

    async def highlight(self, selector: str) -> dict:
        """Flash a red border on an element for 3 seconds (visual debugging)."""
        return await self._send("highlight", {"selector": selector})

    # ---- Page content ----

    async def eval(self, expression: str) -> Any:
        """Execute JavaScript and return the result value.

        Returns the actual JS value (string, number, list, dict, None).
        Raises RuntimeError on failure.
        """
        r = await self._send("eval", {"expression": expression})
        if r.get("success"):
            return r.get("value")
        raise RuntimeError(r.get("error", "eval failed"))

    async def eval_json(self, expression: str) -> Any:
        """Execute JS and auto-parse the result as JSON.

        If the result is already a JSON string it gets parsed.
        Otherwise returns the raw value.
        """
        val = await self.eval(expression)
        if isinstance(val, str):
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                return val
        return val

    async def screenshot(self) -> bytes:
        """Take a screenshot. Returns PNG/JPEG bytes."""
        r = await self._send("screenshot")
        if not r.get("success"):
            raise RuntimeError(r.get("error", "screenshot failed"))
        return base64.b64decode(r["data"])

    async def screenshot_to_file(self, path: str) -> str:
        """Take a screenshot and save to a file. Returns the path."""
        data = await self.screenshot()
        with open(path, "wb") as f:
            f.write(data)
        return path

    async def snapshot(self) -> str:
        """Get the page's accessibility tree as text (similar to browser_snapshot)."""
        r = await self._send("snapshot")
        if r.get("success"):
            return r.get("snapshot", "")
        raise RuntimeError(r.get("error", "snapshot failed"))

    async def get_html(self) -> str:
        """Get the full HTML of the current page."""
        r = await self._send("get_html")
        return r.get("html", "")

    async def get_text(self, expression: str = None) -> str:
        """Get visible text from the page (or a custom JS expression)."""
        params = {}
        if expression:
            params["expression"] = expression
        r = await self._send("get_text", params)
        return r.get("text", "")

    async def get_page_info(self) -> dict:
        """Get current page title and URL. Returns {title, url}."""
        return await self._send("get_page_info")

    async def get_attributes(self, selector: str) -> dict:
        """Get all attributes of an element. Returns {attributes: {...}}."""
        return await self._send("get_attributes", {"selector": selector})

    async def get_cookies(self) -> list:
        """Get all browser cookies."""
        r = await self._send("get_cookies")
        return r.get("cookies", [])

    async def clear_cookies(self) -> dict:
        """Clear all browser cookies."""
        return await self._send("clear_cookies")

    # ---- Wait ----

    async def wait_for(self, selector: str, timeout: int = 10) -> dict:
        """Wait for an element to appear in the DOM.

        Polls every 0.5s. Returns {waited: seconds} or raises on timeout.
        """
        return await self._send("wait_for", {"selector": selector, "timeout": timeout})

    # ---- Chrome management ----

    async def restart_chrome(self) -> dict:
        """Restart Chrome (kills and re-launches)."""
        return await self._send("restart_chrome")


class SyncClient:
    """Synchronous wrapper around CDPClient.

    Designed for use in Hermes execute_code(), Jupyter notebooks,
    and scripts where async is inconvenient.

    Example:
        from cdp_agent_client import SyncClient
        b = SyncClient()
        b.navigate("https://www.baidu.com")
        print(b.eval("document.title"))
    """

    def __init__(self, ws_url: str = "ws://192.168.50.229:19400"):
        self.ws_url = ws_url
        self._client = None

    def _get(self):
        if not self._client:
            self._client = CDPClient(self.ws_url)
        return self._client

    def _run(self, coro):
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(asyncio.run, coro).result()
        except RuntimeError:
            pass
        return asyncio.run(coro)

    def check(self) -> bool:
        return self._run(self._get().ping())

    def ping(self) -> bool:
        return self.check()

    def navigate(self, url: str, wait: float = 2) -> dict:
        r = self._run(self._get().navigate(url))
        if wait:
            time.sleep(wait)
        return r

    def click(self, selector: str = None, text: str = None) -> dict:
        return self._run(self._get().click(selector=selector, text=text))

    def type(self, selector: str, text: str, clear_first: bool = True) -> dict:
        return self._run(self._get().type(selector, text, clear_first))

    def set_value(self, selector: str, value: str) -> dict:
        return self._run(self._get().set_value(selector, value))

    def key_press(self, key: str = "Enter") -> dict:
        return self._run(self._get().key_press(key))

    def hover(self, selector: str) -> dict:
        return self._run(self._get().hover(selector))

    def eval(self, expression: str) -> Any:
        return self._run(self._get().eval(expression))

    def eval_json(self, expression: str) -> Any:
        return self._run(self._get().eval_json(expression))

    def screenshot(self, filepath: str = None) -> Union[str, bytes]:
        data = self._run(self._get().screenshot())
        if filepath:
            with open(filepath, "wb") as f:
                f.write(data)
            return filepath
        return data

    def snapshot(self) -> str:
        return self._run(self._get().snapshot())

    def scroll(self, direction="down", amount=500) -> dict:
        return self._run(self._get().scroll(direction, amount))

    def scroll_to(self, selector: str) -> dict:
        return self._run(self._get().scroll_to(selector))

    def highlight(self, selector: str) -> dict:
        return self._run(self._get().highlight(selector))

    def reload(self, ignore_cache=False) -> dict:
        return self._run(self._get().reload(ignore_cache))

    def go_back(self) -> dict:
        return self._run(self._get().go_back())

    def go_forward(self) -> dict:
        return self._run(self._get().go_forward())

    def get_page_info(self) -> dict:
        return self._run(self._get().get_page_info())

    def get_html(self) -> str:
        return self._run(self._get().get_html())

    def get_text(self, expression: str = None) -> str:
        return self._run(self._get().get_text(expression))

    def get_attributes(self, selector: str) -> dict:
        return self._run(self._get().get_attributes(selector))

    def get_cookies(self) -> list:
        return self._run(self._get().get_cookies())

    def clear_cookies(self) -> dict:
        return self._run(self._get().clear_cookies())

    def wait_for(self, selector: str, timeout: int = 10) -> dict:
        return self._run(self._get().wait_for(selector, timeout))

    def new_tab(self) -> dict:
        return self._run(self._get().new_tab())

    def close_tab(self) -> dict:
        return self._run(self._get().close_tab())

    def restart_chrome(self) -> dict:
        return self._run(self._get().restart_chrome())

    def close(self):
        self._run(self._get().close())

    def __del__(self):
        if self._client:
            try:
                self._run(self._client.close())
            except Exception:
                pass
