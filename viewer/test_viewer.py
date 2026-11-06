"""Smoke tests for the viewer: bundling, loading from file://, rendering, selection, capture.

    .venv/bin/python -m pytest viewer/test_viewer.py -q

Browser tests run the Playwright headless shell over the DevTools pipe and are skipped when
it is missing. Real runs are tested too when any exist under experiments/results/ (or under
$VIEWER_RUNS_ROOT).
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bundle  # noqa: E402
from cdp import Browser, find_shell, scratch_dir  # noqa: E402

FIXTURE = HERE / "fixtures" / "synthetic-run"
needs_browser = pytest.mark.skipif(find_shell() is None, reason="chrome-headless-shell not installed")


def real_runs(limit=3):
    root = Path(os.environ.get("VIEWER_RUNS_ROOT", HERE.parent / "experiments" / "results"))
    found = sorted(p.parent for p in root.glob("**/layout.json") if (p.parent / "state.jsonl.gz").exists())
    return found[-limit:]


@pytest.fixture
def scratch():
    d = Path(scratch_dir("viewer-test-"))
    yield d
    shutil.rmtree(d, ignore_errors=True)


def write_page(run_dir, scratch, name="page.html"):
    out = scratch / name
    out.write_text(bundle.build_html(run_dir), encoding="utf-8")
    return out


def open_ready(browser, page, hash_=""):
    browser.goto(page.as_uri() + hash_)
    browser.wait_for("window.__viewerReady === true || !!window.__viewerError", timeout=60)
    assert browser.eval("window.__viewerError || null") is None
    assert browser.errors == []


def test_bundle_is_self_contained():
    html = bundle.build_html(FIXTURE)
    assert len(html) < 1_000_000
    assert not re.search(r"""<(script|link|img)[^>]+(src|href)=""", html), "the page must not load external files"
    assert "http://" not in html and "https://" not in html
    assert '"layout":' in html and '"state":' in html


def test_bundle_escapes_script_end_in_logged_text(scratch):
    run = scratch / "run"
    shutil.copytree(FIXTURE, run)
    with open(run / "events.jsonl", "a") as f:
        f.write(json.dumps({"kind": "say", "t": 5, "bee": 0, "text": "</script><b>hi</b>", "heard_by": [1]}) + "\n")
    html = bundle.build_html(run)
    assert html.count("</script>") == 2  # the two <script> elements of the template, nothing more


@needs_browser
def test_page_loads_and_renders_a_frame(scratch):
    page = write_page(FIXTURE, scratch)
    with Browser(1280, 720) as b:
        open_ready(b, page, "#t=30")
        # Bee yellow (#f2c230) must be on the canvas: the frame drew the colony.
        yellow = b.eval("""(() => { const c = document.getElementById('map');
            const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data; let n = 0;
            for (let i = 0; i < d.length; i += 4)
              if (Math.abs(d[i] - 242) < 8 && Math.abs(d[i+1] - 194) < 8 && Math.abs(d[i+2] - 48) < 12) n++;
            return n; })()""")
        assert yellow > 50
        assert b.eval("document.getElementById('season-text').textContent") == "Spring, year 1"
        assert len(b.screenshot()) > 10_000


@needs_browser
def test_click_selects_the_bee_drawn_there(scratch):
    page = write_page(FIXTURE, scratch)
    with Browser(1280, 720) as b:
        open_ready(b, page, "#t=40")
        b.eval("V.render()")
        bee = b.eval("""(() => { const d = V.state.drawn.find(o => o.type === 'bee'), v = V.state.view,
            r = document.getElementById('map').getBoundingClientRect();
            return {id: d.id, x: r.left + d.x * v.scale + v.ox, y: r.top + d.y * v.scale + v.oy}; })()""")
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            b.call("Input.dispatchMouseEvent", {"type": kind, "x": bee["x"], "y": bee["y"], "button": "left",
                                                "clickCount": 1 if kind != "mouseMoved" else 0})
        b.wait_for("V.state.sel !== null", timeout=5)
        assert b.eval("V.state.sel") == {"type": "bee", "id": bee["id"]}
        b.wait_for(f"document.getElementById('panel').textContent.includes('Bee {bee['id']}')", timeout=5)


@needs_browser
def test_capture_frames_are_deterministic(scratch):
    page = write_page(FIXTURE, scratch)
    with Browser(640, 360) as b:
        open_ready(b, page, "#capture&from=20&to=60&step=0.5&bee=1")
        assert b.eval("window.__capture.count") == 81
        shot = lambda i: (b.eval(f"window.__capture.frame({i})"), b.screenshot())[1]
        first, other, again = shot(10), shot(50), shot(10)
        assert first == again
        assert first != other


@needs_browser
@pytest.mark.parametrize("run_dir", real_runs(), ids=lambda p: "/".join(p.parts[-3:]))
def test_real_run_loads(run_dir, scratch):
    page = write_page(run_dir, scratch)
    with Browser(1280, 720) as b:
        open_ready(b, page, "#capture&from=0&step=10")
        last = b.eval("window.__capture.count") - 1
        for i in (0, last // 2, last):
            b.eval(f"window.__capture.frame({i})")
        assert b.errors == []


@needs_browser
def test_play_scrub_zoom_pan_and_pinch(scratch):
    page = write_page(FIXTURE, scratch)
    with Browser(1280, 720) as b:
        open_ready(b, page, "#t=10")
        b.eval("document.getElementById('play').click()")
        b.wait_for("V.state.tau > 10.5", timeout=5)
        b.eval("document.getElementById('play').click()")
        assert b.eval("V.state.playing") is False
        b.eval("const s = document.getElementById('timeline'); s.value = 120; s.dispatchEvent(new Event('input'))")
        assert b.eval("V.state.tau") == 120
        scale0 = b.eval("V.state.view.scale")
        b.call("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": 400, "y": 300, "deltaX": 0, "deltaY": -300})
        b.wait_for(f"V.state.view.scale > {scale0} * 1.2", timeout=5)
        ox0 = b.eval("V.state.view.ox")
        for kind, x in (("mousePressed", 400), ("mouseMoved", 450), ("mouseMoved", 500), ("mouseReleased", 500)):
            b.call("Input.dispatchMouseEvent", {"type": kind, "x": x, "y": 300, "button": "left", "buttons": 1, "clickCount": 1})
        b.wait_for(f"V.state.view.ox > {ox0} + 50", timeout=5)
        scale1 = b.eval("V.state.view.scale")
        touch = lambda kind, pts: b.call("Input.dispatchTouchEvent", {"type": kind, "touchPoints": [
            {"x": x, "y": 300, "id": i} for i, x in enumerate(pts)]})
        touch("touchStart", [400, 500])
        touch("touchMove", [350, 550])
        touch("touchMove", [300, 600])
        touch("touchEnd", [])
        b.wait_for(f"V.state.view.scale > {scale1} * 1.5", timeout=5)
        assert b.errors == []
