"""Bundle one run directory into a single self-contained HTML page that replays it.

    python viewer/bundle.py RUN_DIR [-o out.html]

The page needs no server and no network: the run's logs are inlined (state and events
gzip-compressed, base64-encoded) and decompressed in the browser. Open it from file://.
"""
import argparse
import base64
import gzip
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
JS_FILES = ["data.js", "draw_map.js", "draw_live.js", "panel.js", "input.js", "app.js"]
AI_CONDITIONS = ("full", "no_talk", "no_memory", "labels_good_bad", "frozen_hornets")  # as digital_life.mind


def _gz_b64(raw: bytes) -> str:
    return base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0)).decode("ascii")


def _read_maybe_gz(run_dir: Path, name: str) -> bytes | None:
    """Raw bytes of NAME or NAME.gz, decompressed. None if neither exists."""
    if (run_dir / name).exists():
        return (run_dir / name).read_bytes()
    if (run_dir / (name + ".gz")).exists():
        return gzip.decompress((run_dir / (name + ".gz")).read_bytes())
    return None


def run_name(run_dir: Path) -> str:
    """A readable name: up to the last three path parts (experiment/stamp/seed-n)."""
    parts = run_dir.resolve().parts
    return "/".join(parts[-3:])


def load_run(run_dir: Path) -> dict:
    run_dir = Path(run_dir)
    layout = json.loads((run_dir / "layout.json").read_text())
    if layout.get("format", 1) != 1:
        raise SystemExit(f"{run_dir}: layout format {layout.get('format')} is not supported (expected 1)")
    state = _read_maybe_gz(run_dir, "state.jsonl")
    if state is None:
        raise SystemExit(f"{run_dir}: no state.jsonl.gz")
    events = _read_maybe_gz(run_dir, "events.jsonl") or b""
    metrics_raw = _read_maybe_gz(run_dir, "metrics.jsonl") or b""
    metrics = [json.loads(line) for line in metrics_raw.decode().splitlines() if line.strip()]
    record = json.loads((run_dir / "record.json").read_text()) if (run_dir / "record.json").exists() else {}
    return {
        "name": run_name(run_dir),
        "experiment": record.get("experiment") or layout.get("condition", ""),
        "layout": layout,
        "state": _gz_b64(state),
        "events": _gz_b64(events),
        "metrics": metrics,
        "vocab": vocab_of(record.get("params", {})),
    }


def vocab_of(params: dict) -> str | None:
    """The words the run's AI bees read (src/digital_life/vocab.py); None for scripted bees. Runs from before the
    vocab param existed used the wording now called neutral."""
    if params.get("condition") in AI_CONDITIONS or params.get("policy") == "ai":
        return params.get("vocab", "neutral")
    return None


def _inline_json(obj) -> str:
    # "</" would end the <script> element early; "<\/" is the same string to JSON and JS.
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")


def build_html(run_dir: Path, project: str = "Hearsay") -> str:
    data = load_run(run_dir)
    data["project"] = project
    template = (SRC / "index.html").read_text()
    css = (SRC / "style.css").read_text()
    js = "\n".join(f"// ---- {name}\n" + (SRC / name).read_text() for name in JS_FILES)
    title = re.sub(r"[<>&\"]", "", f"{project}, {data['experiment']} seed {data['layout'].get('seed', '')}")
    html = template.replace("/*__CSS__*/", css).replace("/*__JS__*/", js.replace("</script", "<\\/script"))
    html = html.replace("__TITLE__", title)
    head, tail = html.split("__DATA__", 1)
    return head + _inline_json(data) + tail


def main(argv=None):
    ap = argparse.ArgumentParser(description="Bundle a run directory into one self-contained HTML viewer page.")
    ap.add_argument("run_dir", type=Path, help="a run directory (holds layout.json and state.jsonl.gz)")
    ap.add_argument("-o", "--out", type=Path, help="output HTML (default viewer/out/<run>.html)")
    ap.add_argument("--project", default="Hearsay", help="project name shown in the header")
    args = ap.parse_args(argv)
    out = args.out or HERE / "out" / (re.sub(r"[^A-Za-z0-9._-]+", "_", run_name(args.run_dir)) + ".html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(args.run_dir, args.project), encoding="utf-8")
    print(f"{out} ({out.stat().st_size / 1024:.0f} KB)")
    return out


if __name__ == "__main__":
    main()
