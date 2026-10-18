from types import SimpleNamespace

from streamlit.testing.v1 import AppTest

from autosub.engine import transcribe
from autosub.settings import RecognitionSettings
from autosub.subtitles import Word, make_cues


def test_settings_are_forwarded_to_real_recognition_call():
    import numpy as np
    observed = {}

    class Model:
        def transcribe(self, audio, **options):
            observed.update(options)
            return iter([]), SimpleNamespace(language="en")

    settings = RecognitionSettings(language="en", context="Analog IC tutorial", hotwords="MOSFET, ESP32",
        beam_size=3, automatic_retry=False, temperature=0.2, previous_context=False,
        vad_filter=False, vad_threshold=0.35, silence_ms=500, padding_ms=200,
        compression_threshold=2.0, confidence_threshold=-1.5, no_speech_threshold=0.7)
    _, metadata = transcribe(Model(), np.zeros(16000, dtype="float32"), "turbo", "cpu", settings=settings)
    assert observed["language"] == "en" and observed["hotwords"] == "MOSFET, ESP32"
    assert "Analog IC tutorial" in observed["initial_prompt"]
    assert observed["beam_size"] == 3 and observed["temperature"] == 0.2
    assert observed["condition_on_previous_text"] is False and observed["vad_filter"] is False
    assert observed["vad_parameters"]["min_silence_duration_ms"] == 500
    assert observed["log_prob_threshold"] == -1.5
    assert metadata["settings"] == settings.to_dict()
    assert observed["word_timestamps"] is True


def test_auto_language_and_retry_are_independent():
    options = RecognitionSettings(language=None).recognition_options()
    assert options["language"] is None
    assert options["temperature"] == [0, 0.2, 0.4, 0.6, 0.8, 1]
    assert options["hotwords"] is None


def test_layout_preferences_change_segmentation():
    words = [Word(0, 0.5, "甲，"), Word(0.5, 1, "乙。")]
    assert len(make_cues(words, punctuation="sentence")) == 1
    assert len(make_cues(words, punctuation="frequent")) == 2
    words = [Word(i/10, (i+1)/10, "字") for i in range(30)]
    assert len(make_cues(words, max_lines=1, line_width=10)) == 3
    assert len(make_cues(words, max_lines=2, line_width=20)) == 1


def test_preferences_presets_customization_and_reset():
    app = AppTest.from_string("import streamlit as st\nfrom autosub.settings_ui import preferences\nst.json(preferences().to_dict())")
    app.run()
    assert not app.exception
    app.selectbox(key="recognition_density").select("短句").run()
    assert app.number_input(key="recognition_line_width").value == 18
    assert app.selectbox(key="recognition_max_lines").value == 1
    app.number_input(key="recognition_pause").set_value(0.4).run()
    assert app.selectbox(key="recognition_density").value == "自訂"
    app.text_input(key="recognition_hotwords").set_value("ESP32").run()
    next(button for button in app.button if button.label == "恢復預設設定").click().run()
    assert not app.exception
    assert app.text_input(key="recognition_hotwords").value == ""
    assert app.number_input(key="recognition_pause").value == 0.6
