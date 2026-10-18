"""Audio decoding and local Whisper inference."""
from __future__ import annotations

import hashlib
import io
import os
import sys
import time
from pathlib import Path

from .subtitles import Word, make_cues
from .settings import RecognitionSettings

MAX_SECONDS = 300
MAX_BYTES = 100 * 1024 * 1024
MODEL_NAMES = ("small", "medium", "turbo", "large-v3")
MODEL_DIR = Path(os.environ.get("AUTO_SUB_MODEL_DIR", Path(__file__).resolve().parents[1] / "models"))
_DLL_HANDLES = []


def configure_gpu_libraries() -> None:
    """Discover optional NVIDIA wheels without modifying system-wide PATH."""
    if sys.platform != "win32" or _DLL_HANDLES:
        return
    package_root = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    for component in ("cublas", "cudnn", "cuda_runtime", "cuda_nvrtc"):
        for directory in (package_root / component / "bin", package_root / component / "lib"):
            if directory.is_dir():
                _DLL_HANDLES.append(os.add_dll_directory(str(directory)))
                os.environ["PATH"] = str(directory) + os.pathsep + os.environ.get("PATH", "")


def decode_audio(raw: bytes, filename: str):
    import numpy as np
    if Path(filename).suffix.lower() not in {".mp3", ".wav", ".m4a"}:
        raise ValueError("只接受 MP3、WAV、M4A 音訊檔。")
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("音檔必須介於 1 byte 與 100 MB 之間。")
    # Bound decoded allocation as well as compressed input size. This avoids
    # decoding an arbitrarily long low-bitrate file before checking duration.
    import av
    with av.open(io.BytesIO(raw)) as container:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        chunks = []
        samples = 0
        for frame in container.decode(audio=0):
            frame.pts = None
            for output in resampler.resample(frame):
                chunk = output.to_ndarray().reshape(-1)
                samples += len(chunk)
                if samples > MAX_SECONDS * 16000:
                    raise ValueError("音檔超過 5 分鐘，請先裁切。")
                chunks.append(chunk)
        for output in resampler.resample(None):
            chunk = output.to_ndarray().reshape(-1)
            samples += len(chunk)
            if samples > MAX_SECONDS * 16000:
                raise ValueError("音檔超過 5 分鐘，請先裁切。")
            chunks.append(chunk)
    if not samples:
        raise ValueError("音檔沒有可解碼的音訊。")
    audio = np.concatenate(chunks).astype(np.float32) / 32768.0
    return audio, samples / 16000


def gpu_count() -> int:
    configure_gpu_libraries()
    import ctranslate2
    try:
        return ctranslate2.get_cuda_device_count()
    except RuntimeError:
        return 0


def load_model(name: str, device: str, offline: bool = False):
    configure_gpu_libraries()
    from faster_whisper import WhisperModel

    if name not in MODEL_NAMES or device not in {"cpu", "cuda"}:
        raise ValueError("模型或裝置不合法。")
    compute = "int8" if device == "cpu" else "float16"
    return WhisperModel(name, device=device, compute_type=compute,
                        download_root=str(MODEL_DIR), local_files_only=offline,
                        cpu_threads=min(8, os.cpu_count() or 4), num_workers=1)


def transcribe(model, audio, model_name: str, device: str, line_width: int = 20,
               settings: RecognitionSettings | None = None):
    from opencc import OpenCC

    converter = OpenCC("s2t")
    settings = settings or RecognitionSettings(line_width=line_width)
    started = time.perf_counter()
    segments, info = model.transcribe(audio, **settings.recognition_options())
    words = []
    raw_segments = []
    duration = len(audio) / 16000
    for segment in segments:
        raw_segments.append({"start": segment.start, "end": segment.end,
                             "text": segment.text})
        timed = segment.words or []
        if not timed and segment.text.strip():
            timed = [Word(segment.start, segment.end, segment.text)]
        for item in timed:
            start = max(0.0, min(float(item.start), duration))
            end = max(start, min(float(item.end), duration))
            text = converter.convert(item.word if hasattr(item, "word") else item.text)
            if words:
                start = max(start, words[-1].end)
            if end <= start:
                # Punctuation can have zero duration; attach it to its neighbor.
                if words:
                    words[-1].text += text
                continue
            words.append(Word(start, end, text))
    elapsed = time.perf_counter() - started
    metadata = {"model": model_name, "device": device,
                "transcription_seconds": round(elapsed, 3),
                "language": info.language, "raw_segments": raw_segments, "settings": settings.to_dict(),
                "words": [{"start": w.start, "end": w.end, "text": w.text} for w in words]}
    return make_cues(words, **settings.layout_options()), metadata


def audio_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def recognize_boundaries(model, audio, cues, model_name: str, device: str,
                         settings: RecognitionSettings | None = None):
    """Re-transcribe bounded regions; preserve text and all manually set times."""
    from .editing import pending_groups, recover_times
    words = []
    for left, right in pending_groups(cues):
        start, end = cues[left].start, cues[right].end
        if start is None or end is None or not 0 <= start < end <= len(audio) / 16000:
            continue
        _, metadata = transcribe(model, audio[round(start*16000):round(end*16000)], model_name, device,
                                 settings=settings)
        words.extend(Word(w["start"] + start, w["end"] + start, w["text"])
                     for w in metadata["words"])
    return recover_times(cues, words)
