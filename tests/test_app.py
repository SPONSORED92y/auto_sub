from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_initial_page_loads_without_downloading_a_model():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"))
    app.run(timeout=30)
    assert not app.exception
    assert app.title[0].value == "Auto Sub 本機字幕"
    assert len(app.get("file_uploader")) == 1
    assert app.info
    model = next(box for box in app.selectbox if "模型" in box.label)
    assert model.options == ["small", "medium", "turbo", "large-v3"]


def test_loaded_subtitles_render_without_obsolete_controls(monkeypatch):
    import io
    import wave
    from types import SimpleNamespace
    import streamlit as st
    from autosub.engine import audio_hash
    from autosub.subtitles import Cue

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 32000)
    raw = buffer.getvalue()
    uploaded = SimpleNamespace(name="test.wav", getvalue=lambda: raw)
    monkeypatch.setattr(st, "file_uploader", lambda label, **kwargs:
                        None if kwargs.get("key") == "project_upload" else uploaded)
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"))
    app.session_state["digest"] = audio_hash(raw)
    app.session_state["cues"] = [Cue(0.2, 1.2, "測試 English")]
    app.session_state["metadata"] = {"model": "test"}
    app.session_state["revision"] = 1
    app.run(timeout=30)
    assert not app.exception
    assert "測試 English" in app.code[0].value
    assert not any(box.label == "跳至字幕" for box in app.selectbox)
    assert not any(button.label == "從這句播放" for button in app.button)
    assert app.get("component_instance")
