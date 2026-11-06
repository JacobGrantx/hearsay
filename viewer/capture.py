"""Render a bundled viewer page to video (or one still), headless and deterministic.

    python viewer/capture.py RUN_HTML OUT.mp4 --from 0 --to 400 --step 0.5 --fps 30
    python viewer/capture.py RUN_HTML still.png --from 120 [--bee 3]

Each frame is the page in capture mode (#capture&from=..&to=..&step=..) rendering tick
from + i * step from the inlined logs alone, then screenshotted. Frames go to a scratch
directory on /dev/shm and are deleted after ffmpeg encodes them.
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cdp import Browser, CDPError, scratch_dir  # noqa: E402


def capture_hash(t0, t1=None, step=1.0, bee=None, view=None):
    h = f"#capture&from={t0:g}&step={step:g}"
    if t1 is not None:
        h += f"&to={t1:g}"
    if bee is not None:
        h += f"&bee={bee}"
    if view:
        h += f"&view={view}"
    return h


def open_page(browser, html: Path, hash_: str, timeout=120):
    """Load the page in capture mode and return its frame count."""
    browser.goto(html.resolve().as_uri() + hash_)
    browser.wait_for("window.__viewerReady === true || !!window.__viewerError", timeout=timeout)
    err = browser.eval("window.__viewerError || null")
    if err:
        raise CDPError("the viewer failed to load: " + err)
    return browser.eval("window.__capture.count")


def render_frames(browser, frames_dir: Path, count: int, quiet=False):
    start = time.monotonic()
    for i in range(count):
        browser.eval(f"window.__capture.frame({i})")
        (frames_dir / f"f{i:06d}.png").write_bytes(browser.screenshot())
        if not quiet and (i + 1) % 100 == 0:
            rate = (i + 1) / (time.monotonic() - start)
            print(f"  frame {i + 1} of {count} ({rate:.1f} per second)", file=sys.stderr)


def encode(frames_dir: Path, out: Path, fps: float):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", f"{fps:g}", "-i", str(frames_dir / "f%06d.png"),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render a bundled viewer page to MP4 or PNG, headless.")
    ap.add_argument("html", type=Path, help="a page written by viewer/bundle.py")
    ap.add_argument("out", type=Path, help="output .mp4, or .png for a single still at --from")
    ap.add_argument("--from", dest="t0", type=float, default=0.0, help="first tick (default 0)")
    ap.add_argument("--to", dest="t1", type=float, default=None, help="last tick (default: the run's last)")
    ap.add_argument("--step", type=float, default=0.5, help="ticks per frame (default 0.5)")
    ap.add_argument("--fps", type=float, default=30.0, help="frames per second of video (default 30)")
    ap.add_argument("--bee", type=int, default=None, help="select this bee, so the panel follows it")
    ap.add_argument("--view", default=None, help="frame a region of cells: x0,y0,x1,y1")
    ap.add_argument("--size", default="1280x720", help="viewport WIDTHxHEIGHT (default 1280x720)")
    args = ap.parse_args(argv)
    if args.step <= 0:
        ap.error("--step must be positive")
    if not args.html.exists():
        ap.error(f"{args.html} does not exist")
    width, height = (int(v) for v in args.size.lower().split("x"))
    still = args.out.suffix.lower() == ".png"
    hash_ = capture_hash(args.t0, args.t0 if still else args.t1, args.step, args.bee, args.view)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    with Browser(width, height) as browser:
        count = open_page(browser, args.html, hash_)
        if still:
            browser.eval("window.__capture.frame(0)")
            args.out.write_bytes(browser.screenshot())
            print(args.out)
            return args.out
        if shutil.which("ffmpeg") is None:
            raise SystemExit("ffmpeg is not on PATH")
        print(f"{count} frames, {count / args.fps:.1f} s of video", file=sys.stderr)
        frames_dir = Path(scratch_dir("viewer-frames-"))
        try:
            render_frames(browser, frames_dir, count)
            if browser.errors:
                print("page errors:\n  " + "\n  ".join(browser.errors[:10]), file=sys.stderr)
            encode(frames_dir, args.out, args.fps)
        finally:
            shutil.rmtree(frames_dir, ignore_errors=True)
    print(f"{args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")
    return args.out


if __name__ == "__main__":
    main()
