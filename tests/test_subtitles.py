import json

import pytest

from autosub.subtitles import Cue, Word, load_project, make_cues, save_project, to_srt, validate, wrap_text


def test_bilingual_words_and_pause_keep_original_time():
    words = [Word(0.2, 0.5, "這是"), Word(0.5, 1, " ESP32"),
             Word(1, 1.5, " Arduino"), Word(2.5, 3, "測試。")]
    cues = make_cues(words)
    assert len(cues) == 2
    assert cues[0].text == "這是 ESP32 Arduino"
    assert (cues[0].start, cues[0].end) == (0.2, 1.5)
    assert cues[1].start == 2.5


def test_layout_splits_cues_without_breaking_english_words():
    words = [Word(i * 0.1, (i+1) * 0.1, "字") for i in range(90)]
    cues = make_cues(words)
    assert len(cues) == 3
    assert all(len(c.text.splitlines()) <= 2 for c in cues)
    assert "microcontroller" in wrap_text("字" * 18 + " microcontroller", 20)
    assert "".join(c.text.replace("\n", "") for c in cues) == "字" * 90


def test_wrap_prefers_clause_boundary():
    assert wrap_text("接下來我們會產生字幕檔,並檢查時間是否正確。", 20) == (
        "接下來我們會產生字幕檔,\n並檢查時間是否正確。")


def test_srt_rounds_milliseconds_and_rejects_overlap():
    assert to_srt([Cue(59.9996, 61.2, "測試\nHello")], 62) == (
        "1\n00:01:00,000 --> 00:01:01,200\n測試\nHello\n")
    with pytest.raises(ValueError):
        to_srt([Cue(0, 2, "A"), Cue(1, 3, "B")], 3)


@pytest.mark.parametrize("cue", [Cue(-1, 2, "A"), Cue(1, 1, "A"), Cue(0, 4, "A"),
    Cue(float("nan"), 2, "A"), Cue(0, 1, ""), Cue(0, 1, "A\n\nB"), Cue(0, 0.0001, "A")])
def test_invalid_edits_are_blocked(cue):
    assert validate([cue], 3)


def test_project_roundtrip_and_audio_identity():
    cues = [Cue(0, 1, "繁體 English")]
    raw = save_project(cues, 2, "audio1", {"model": "turbo"})
    restored, metadata = load_project(raw, "audio1", 2)
    assert restored == cues
    assert metadata["model"] == "turbo"
    with pytest.raises(ValueError, match="音檔不相符"):
        load_project(raw, "audio2", 2)
    data = json.loads(raw)
    data["schema_version"] = 99
    with pytest.raises(ValueError):
        load_project(json.dumps(data), "audio1", 2)
