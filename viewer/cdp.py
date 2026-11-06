"""A minimal Chrome DevTools Protocol client over --remote-debugging-pipe.

No packages beyond the standard library: the headless shell reads commands on fd 3 and
writes replies on fd 4, each message a JSON object ended by a NUL byte.
"""
import base64
import fcntl
import glob
import json
import os
import select
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

PLAYWRIGHT_SHELL = (Path.home() / ".cache/ms-playwright/chromium_headless_shell-1243"
                    / "chrome-headless-shell-linux64/chrome-headless-shell")


def find_shell() -> str | None:
    """The headless shell: $VIEWER_CHROME, then Playwright's 1243 build, then any other build."""
    found = [os.environ.get("VIEWER_CHROME", ""), str(PLAYWRIGHT_SHELL)]
    found += sorted(glob.glob(str(Path.home() / ".cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell")),
                    reverse=True)
    return next((p for p in found if p and os.access(p, os.X_OK)), None)


def scratch_dir(prefix: str) -> str:
    """A fresh directory on /dev/shm when it exists (the VM's disk is tight), else the system temp dir."""
    return tempfile.mkdtemp(prefix=prefix, dir="/dev/shm" if os.path.isdir("/dev/shm") else None)


class CDPError(RuntimeError):
    pass


class Browser:
    """One headless page of a fixed size. Use as a context manager."""

    def __init__(self, width=1280, height=720, binary=None):
        binary = binary or find_shell()
        if not binary:
            raise CDPError("chrome-headless-shell not found; set VIEWER_CHROME to its path")
        self.width, self.height = width, height
        self.profile = scratch_dir("viewer-chrome-")
        self.errors, self._events, self._buf, self._next_id = [], [], b"", 0
        # Move the pipe ends above fd 10 so placing them on fds 3 and 4 in the child cannot clash.
        to_child_r, self._w = os.pipe()
        self._r, from_child_w = os.pipe()
        hi_r = fcntl.fcntl(to_child_r, fcntl.F_DUPFD_CLOEXEC, 10)
        hi_w = fcntl.fcntl(from_child_w, fcntl.F_DUPFD_CLOEXEC, 10)
        os.close(to_child_r)
        os.close(from_child_w)

        def child_fds():
            os.dup2(hi_r, 3)
            os.dup2(hi_w, 4)

        args = [binary, "--headless", "--no-sandbox", "--remote-debugging-pipe",
                f"--user-data-dir={self.profile}", f"--window-size={width},{height}",
                "--hide-scrollbars", "--force-device-scale-factor=1", "--mute-audio", "--no-first-run",
                "--disable-gpu", "--disable-extensions", "--disable-background-networking",
                "--font-render-hinting=none", "about:blank"]
        self._log = open(os.path.join(self.profile, "stderr.log"), "wb")
        self.proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=self._log, preexec_fn=child_fds, close_fds=False)
        os.close(hi_r)
        os.close(hi_w)
        try:
            pages = [t for t in self._call("Target.getTargets")["targetInfos"] if t["type"] == "page"]
            target = pages[0]["targetId"] if pages else self._call("Target.createTarget", {"url": "about:blank"})["targetId"]
            self.session = self._call("Target.attachToTarget", {"targetId": target, "flatten": True})["sessionId"]
            self.call("Page.enable")
            self.call("Runtime.enable")
            self.call("Emulation.setDeviceMetricsOverride",
                      {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})
        except Exception:
            self.close()
            raise

    # -- protocol
    def _send(self, method, params=None, session=None):
        self._next_id += 1
        msg = {"id": self._next_id, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        os.write(self._w, json.dumps(msg).encode() + b"\0")
        return self._next_id

    def _read(self, timeout):
        while b"\0" not in self._buf:
            ready, _, _ = select.select([self._r], [], [], timeout)
            if not ready:
                raise CDPError("timed out waiting for the browser")
            chunk = os.read(self._r, 1 << 20)
            if not chunk:
                raise CDPError("browser closed the pipe; see " + os.path.join(self.profile, "stderr.log"))
            self._buf += chunk
        raw, self._buf = self._buf.split(b"\0", 1)
        return json.loads(raw)

    def _call(self, method, params=None, session=None, timeout=60):
        mid = self._send(method, params, session)
        deadline = time.monotonic() + timeout
        while True:
            msg = self._read(max(0.05, deadline - time.monotonic()))
            if msg.get("id") == mid:
                if "error" in msg:
                    raise CDPError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            self._on_event(msg)

    def _on_event(self, msg):
        method, params = msg.get("method"), msg.get("params", {})
        if method == "Runtime.exceptionThrown":
            d = params.get("exceptionDetails", {})
            self.errors.append(d.get("exception", {}).get("description") or d.get("text", "exception"))
        elif method == "Runtime.consoleAPICalled" and params.get("type") == "error":
            self.errors.append(" ".join(str(a.get("value", a.get("description", ""))) for a in params.get("args", [])))

    def call(self, method, params=None, timeout=60):
        return self._call(method, params, self.session, timeout)

    # -- page helpers
    def goto(self, url, timeout=60):
        self.call("Page.navigate", {"url": url}, timeout)

    def eval(self, expression, timeout=60):
        res = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True,
                                             "awaitPromise": True}, timeout)
        if "exceptionDetails" in res:
            d = res["exceptionDetails"]
            raise CDPError(d.get("exception", {}).get("description") or d.get("text", "evaluation failed"))
        return res.get("result", {}).get("value")

    def wait_for(self, expression, timeout=60, interval=0.05):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.eval(expression):
                return True
            time.sleep(interval)
        raise CDPError(f"timed out waiting for: {expression}")

    def screenshot(self) -> bytes:
        res = self.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        return base64.b64decode(res["data"])

    def close(self):
        try:
            if self.proc.poll() is None:
                try:
                    self._send("Browser.close")
                    self.proc.wait(timeout=5)
                except Exception:
                    self.proc.kill()
                    self.proc.wait(timeout=5)
        finally:
            for fd in (self._r, self._w):
                try:
                    os.close(fd)
                except OSError:
                    pass
            self._log.close()
            shutil.rmtree(self.profile, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
