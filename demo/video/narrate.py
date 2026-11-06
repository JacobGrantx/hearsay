"""Speak the storyboard's narration: one WAV per segment, with Kokoro-82M run locally (kokoro-onnx).

Each segment's `narration` line in storyboard.py is synthesised with voice af_heart, then given a little
low-mid warmth and gentle compression by ffmpeg. Loudness is normalised later, on the whole track, by
make_video.py. A WAV is only re-spoken when its line changes (the line is kept next to it as <id>.txt).

Needs the packages in requirements-video.txt and the two model files (kokoro-v1.0.onnx and
voices-v1.0.bin from kokoro-onnx's model-files-v1.0 release), found in --models or $KOKORO_MODELS.
"""
import argparse
import json
import os
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from storyboard import SEGMENTS  # noqa: E402

VOICE, SPEED, LANG = "af_heart", 1.0, "en-us"
# Warmth: a soft shelf around 200 Hz and a touch of presence; then 2.5:1 compression. Nothing heavier.
TONE = ("highpass=f=70,equalizer=f=200:t=q:w=1.2:g=2.5,equalizer=f=3200:t=q:w=1.5:g=1.0,"
        "acompressor=threshold=0.125:ratio=2.5:attack=12:release=180:makeup=1.4")


def lines() -> dict:
    return {s["id"]: s["narration"] for s in SEGMENTS if s.get("narration")}


def seconds(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def track(segments: list, folder: Path, out: Path, lead: float, rate: int = 24000) -> None:
    """One mono WAV as long as the video: each segment's line starts `lead` s after its segment does."""
    import numpy as np
    total = int(round(sum(s["seconds"] for s in segments) * rate))
    buf, start = np.zeros(total + rate, dtype=np.int16), 0.0
    for s in segments:
        if s.get("narration"):
            with wave.open(str(folder / f"{s['id']}.wav")) as w:
                pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
            i = int(round((start + lead) * rate))
            buf[i:i + len(pcm)] = pcm
        start += s["seconds"]
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
        w.writeframes(buf[:total].tobytes())


def normalise(src: Path, out: Path, lufs: float = -16.0, peak: float = -1.5) -> dict:
    """Two-pass EBU R128 normalisation (ffmpeg loudnorm, linear). Returns the first pass's measures."""
    f = f"loudnorm=I={lufs}:TP={peak}:LRA=11"
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af", f + ":print_format=json", "-f", "null",
                        "-"], capture_output=True, text=True, check=True)
    m = json.loads(p.stderr[p.stderr.rindex("{"):])
    f += (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", f, "-ar", "48000", str(out)],
                   check=True)
    return m


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Write one narration WAV per storyboard segment.")
    ap.add_argument("--out", type=Path, required=True, help="directory for <segment id>.wav")
    ap.add_argument("--models", type=Path, default=Path(os.environ.get("KOKORO_MODELS", "~/.cache/kokoro")),
                    help="directory holding kokoro-v1.0.onnx and voices-v1.0.bin (default $KOKORO_MODELS)")
    args = ap.parse_args(argv)
    models = args.models.expanduser()
    args.out.mkdir(parents=True, exist_ok=True)
    todo = {k: v for k, v in lines().items()
            if not ((args.out / f"{k}.wav").exists() and (args.out / f"{k}.txt").read_text() == v)}
    if todo:
        import soundfile as sf
        from kokoro_onnx import Kokoro
        kokoro = Kokoro(str(models / "kokoro-v1.0.onnx"), str(models / "voices-v1.0.bin"))
        for key, text in todo.items():
            samples, rate = kokoro.create(text, voice=VOICE, speed=SPEED, lang=LANG)
            raw = args.out / f"{key}.raw.wav"
            sf.write(raw, samples, rate)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af", TONE, "-ar", "24000",
                            "-ac", "1", "-c:a", "pcm_s16le", str(args.out / f"{key}.wav")], check=True)
            raw.unlink()
            (args.out / f"{key}.txt").write_text(text)
            print(f"{key}: {len(samples) / rate:.2f} s", file=sys.stderr)
    print(f"{len(lines())} lines in {args.out} ({len(todo)} spoken now)", file=sys.stderr)


if __name__ == "__main__":
    main()
