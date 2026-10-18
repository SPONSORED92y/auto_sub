"""Reproducible local transcription smoke test and model comparison."""
import argparse
import json
from pathlib import Path
import time

from autosub.engine import audio_hash, decode_audio, load_model, transcribe
from autosub.subtitles import save_project, to_srt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--model", choices=["turbo", "large-v3", "small", "medium"], default="turbo")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    raw = args.audio.read_bytes()
    audio, duration = decode_audio(raw, args.audio.name)
    start = time.perf_counter()
    model = load_model(args.model, args.device, args.offline)
    load_seconds = time.perf_counter() - start
    cues, metadata = transcribe(model, audio, args.model, args.device)
    metadata["model_access_seconds"] = round(load_seconds, 3)
    args.output.mkdir(parents=True, exist_ok=True)
    stem = f"{args.audio.stem}.{args.model}.{args.device}"
    (args.output / f"{stem}.srt").write_text(to_srt(cues, duration), encoding="utf-8")
    (args.output / f"{stem}.autosub.json").write_text(
        save_project(cues, duration, audio_hash(raw), metadata), encoding="utf-8")
    print(json.dumps({"model": args.model, "device": args.device,
                      "duration": round(duration, 3), "cues": len(cues),
                      "model_access_seconds": metadata["model_access_seconds"],
                      "transcription_seconds": metadata["transcription_seconds"],
                      "output": str(args.output.resolve())}, ensure_ascii=False))


if __name__ == "__main__":
    main()
