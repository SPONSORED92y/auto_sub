"""Cursor-aware audio/subtitle editor rendered in an isolated iframe."""
import base64
from dataclasses import asdict
from pathlib import Path

import streamlit.components.v1 as components

_editor = components.declare_component("subtitle_editor", path=str(Path(__file__).with_name("editor_frontend")))


def subtitle_editor(cues, raw: bytes, mime: str, digest: str, duration: float, revision: int):
    return _editor(cues=[asdict(c) for c in cues], audio_src=f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}",
                   digest=digest, duration=duration, revision=revision, key=f"editor-{digest}", default=None)
