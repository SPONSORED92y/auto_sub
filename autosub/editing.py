"""Conservative timing recovery for user-created subtitle boundaries.

Only accept exact normalized text matches at real word boundaries. Never
interpolate character positions or overwrite user-filled times.
"""
from dataclasses import replace
import unicodedata

from .subtitles import Cue, Word


def normalize(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold() if c.isalnum())


def pending_groups(cues: list[Cue]) -> list[tuple[int, int]]:
    groups = []
    for i in range(len(cues) - 1):
        if cues[i].end is not None and cues[i+1].start is not None:
            continue
        left, right = i, i + 1
        while left > 0 and cues[left].start is None:
            left -= 1
        while right < len(cues)-1 and cues[right].end is None:
            right += 1
        group = (left, right)
        if group not in groups:
            groups.append(group)
    merged = []
    for left, right in sorted(groups):
        if merged and left <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], right))
        else:
            merged.append((left, right))
    return merged


def recover_times(cues: list[Cue], words: list[Word]) -> tuple[list[Cue], int]:
    result = [replace(c) for c in cues]
    recovered = 0
    for left, right in pending_groups(cues):
        start, end = cues[left].start, cues[right].end
        if start is None or end is None or end <= start:
            continue
        timed = [w for w in words if w.start >= start - 0.025 and w.end <= end + 0.025
                 and normalize(w.text)]
        expected = "".join(normalize(c.text) for c in cues[left:right+1])
        if not expected or expected != "".join(normalize(w.text) for w in timed):
            continue
        positions, offset = {}, 0
        for j, word in enumerate(timed[:-1]):
            offset += len(normalize(word.text))
            positions[offset] = (word.end, timed[j+1].start)
        offset = 0
        for i in range(left, right):
            offset += len(normalize(cues[i].text))
            if offset not in positions:
                continue
            end_time, start_time = positions[offset]
            end_time = result[i].end if result[i].end is not None else end_time
            start_time = result[i+1].start if result[i+1].start is not None else start_time
            if (end_time > start_time or
                (result[i].start is not None and end_time <= result[i].start) or
                (result[i+1].end is not None and start_time >= result[i+1].end)):
                continue
            if result[i].end is None or result[i+1].start is None:
                result[i].end, result[i+1].start = round(end_time, 3), round(start_time, 3)
                recovered += 1
    return result, recovered
