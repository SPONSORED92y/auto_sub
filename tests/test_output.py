import pytest

from autosub.output import format_punctuation
from autosub.subtitles import Cue, to_srt


@pytest.mark.parametrize("mode,expected", [
    ("keep", "今天測試，明天再看。"),
    ("remove", "今天測試明天再看"),
    ("spaces", "今天測試 明天再看"),
])
def test_output_choices(mode, expected):
    assert format_punctuation("今天測試，明天再看。", mode) == expected


@pytest.mark.parametrize("mode", ["remove", "spaces"])
def test_common_technical_punctuation_is_preserved(mode):
    text = "3.3V Wi-Fi don't ESP32-S3 C++ C# 1,000 50% 12:30 test@example.com https://example.com/a?q=1!"
    assert format_punctuation(text, mode) == text[:-1]


def test_spaces_and_empty_lines_are_normalized_without_erasing_line_breaks():
    assert format_punctuation("「你好」，  世界！\n。\n(Hello, world.)", "spaces") == "你好 世界\nHello world"
    assert format_punctuation("你好。世界", "remove") == "你好世界"


def test_srt_filter_keeps_times_source_and_contiguous_numbering():
    cues = [Cue(0,1,"你好，世界。"), Cue(1,2,"？！"), Cue(2,3,"Hello!")]
    srt = to_srt(cues, 3, punctuation_mode="spaces")
    assert "00:00:00,000 --> 00:00:01,000\n你好 世界" in srt
    assert "2\n00:00:02,000 --> 00:00:03,000\nHello" in srt
    assert cues[0].text == "你好，世界。" and cues[1].text == "？！"


def test_invalid_output_mode_is_rejected():
    with pytest.raises(ValueError):
        format_punctuation("文字", "unknown")


def test_url_does_not_swallow_adjacent_chinese_sentence_punctuation():
    assert format_punctuation("網址 https://example.com。繼續，測試！", "spaces") == (
        "網址 https://example.com 繼續 測試")
