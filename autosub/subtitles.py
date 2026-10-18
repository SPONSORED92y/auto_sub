"""Subtitle layout and serialization, independent of the inference runtime."""
from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import asdict, dataclass


@dataclass
class Word:
    start: float
    end: float
    text: str


@dataclass
class Cue:
    start: float | None
    end: float | None
    text: str


def width(text: str) -> float:
    # One CJK glyph is one unit; Latin glyphs are half a unit.
    return sum(1 if unicodedata.east_asian_width(c) in "WF" else 0.5 for c in text)


def join_text(left: str, right: str) -> str:
    if not left:
        return right.strip()
    if not right.strip():
        return left
    # Whisper tokens often include leading whitespace for English words.
    needs_space = right[0].isspace() or (
        left[-1].isascii() and left[-1].isalnum()
        and right[0].isascii() and right[0].isalnum()
    )
    return left.rstrip() + (" " if needs_space else "") + right.strip()


def wrap_text(text: str, line_width: int = 20) -> str:
    tokens = re.findall(r"[A-Za-z0-9]+(?:['’._+-][A-Za-z0-9]+)*|\s+|.", text.strip())
    lines: list[str] = []
    current = ""
    for token in tokens:
        if current and width(current + token) > line_width and not token.isspace():
            # Prefer a nearby clause boundary over cutting a Chinese phrase.
            boundaries = [match.end() for match in re.finditer(r"[，,；;：:。！？!?]", current)
                          if width(current[:match.end()]) >= line_width * 0.4]
            if boundaries:
                split = boundaries[-1]
                lines.append(current[:split].rstrip())
                current = current[split:].lstrip() + token
            else:
                lines.append(current.rstrip())
                current = token
        else:
            current += token
    if current.strip():
        lines.append(current.strip())
    return "\n".join(lines)


def make_cues(words: list[Word], line_width: int = 20, pause: float = 0.6,
              max_duration: float = 6.0, max_lines: int = 2,
              punctuation: str = "standard") -> list[Cue]:
    """Group timed words without inventing internal timestamps for long tokens.

    A token with more than two lines is kept intact: fake time interpolation
    would hide alignment uncertainty. The UI reports such layout exceptions.
    """
    cues: list[Cue] = []
    group: list[Word] = []
    text = ""

    def flush() -> None:
        nonlocal group, text
        if group:
            cues.append(Cue(group[0].start, group[-1].end, wrap_text(text, line_width)))
        group, text = [], ""

    for word in words:
        if not word.text.strip():
            continue
        candidate = join_text(text, word.text)
        if group and (
            word.start - group[-1].end >= pause
            or word.end - group[0].start > max_duration
            or len(wrap_text(candidate, line_width).splitlines()) > max_lines
        ):
            flush()
        group.append(word)
        text = join_text(text, word.text)
        if re.search(r"[。！？!?]$", text) or (
            re.search(r"[，,；;：:]$", text) and (
                punctuation == "frequent" or
                (punctuation == "standard" and width(text) >= line_width * 0.6))
        ):
            flush()
    flush()
    return cues


def validate(cues: list[Cue], duration: float, allow_pending: bool = False) -> list[str]:
    errors: list[str] = []
    previous_end = 0.0
    for i, cue in enumerate(cues, 1):
        pending = cue.start is None or cue.end is None
        if pending and not allow_pending:
            errors.append(f"第 {i} 句斷句時間尚未填寫。")
        values = [v for v in (cue.start, cue.end) if v is not None]
        numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool)
                      and math.isfinite(v) for v in values)
        if not numeric:
            errors.append(f"第 {i} 句時間必須是有限數字。")
        elif any(v < 0 or v > duration + 0.001 for v in values):
            errors.append(f"第 {i} 句起訖時間不合法或超出音檔。")
        elif not pending and round(cue.end * 1000) <= round(cue.start * 1000):
            errors.append(f"第 {i} 句在毫秒精度下長度為零。")
        if numeric:
            first = cue.start if cue.start is not None else cue.end
            if first is not None and round(first * 1000) < round(previous_end * 1000):
                errors.append(f"第 {i} 句與前一句重疊或順序錯誤。")
            if cue.end is not None:
                previous_end = cue.end
            elif cue.start is not None:
                previous_end = cue.start
        if not isinstance(cue.text, str) or not cue.text.strip():
            errors.append(f"第 {i} 句文字不可空白。")
        elif any(not line.strip() for line in cue.text.strip().splitlines()):
            errors.append(f"第 {i} 句包含空白行，請移除。")
        elif any(ord(c) < 32 and c not in "\n\t\r" for c in cue.text):
            errors.append(f"第 {i} 句包含不支援的控制字元。")
    return errors


def timestamp(seconds: float) -> str:
    total = round(seconds * 1000)
    hours, total = divmod(total, 3_600_000)
    minutes, total = divmod(total, 60_000)
    secs, millis = divmod(total, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def to_srt(cues: list[Cue], duration: float, punctuation_mode: str = "keep") -> str:
    from .output import format_punctuation
    errors = validate(cues, duration)
    if errors:
        raise ValueError("\n".join(errors))
    formatted = [Cue(c.start, c.end, format_punctuation(c.text, punctuation_mode)) for c in cues]
    formatted = [c for c in formatted if c.text.strip()]
    return "\n\n".join(
        f"{i}\n{timestamp(c.start)} --> {timestamp(c.end)}\n{c.text.strip()}"
        for i, c in enumerate(formatted, 1)
    ) + ("\n" if formatted else "")


def save_project(cues: list[Cue], duration: float, audio_sha256: str,
                 metadata: dict) -> str:
    return json.dumps({"schema_version": 2, "duration": duration,
                       "audio_sha256": audio_sha256, "metadata": metadata,
                       "cues": [asdict(c) for c in cues]}, ensure_ascii=False, indent=2)


def load_project(raw: str, audio_sha256: str, duration: float) -> tuple[list[Cue], dict]:
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("schema_version") not in (1, 2):
        raise ValueError("不支援的專案格式。")
    if data.get("audio_sha256") != audio_sha256:
        raise ValueError("專案與目前音檔不相符，請選擇原始音檔。")
    if not isinstance(data.get("cues"), list) or len(data["cues"]) > 10000:
        raise ValueError("字幕資料格式或數量不合法。")
    cues = [Cue(**item) for item in data["cues"]]
    errors = validate(cues, duration, allow_pending=True)
    if errors:
        raise ValueError("\n".join(errors))
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("專案 metadata 格式不合法。")
    return cues, metadata
