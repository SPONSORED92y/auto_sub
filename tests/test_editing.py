import pytest

from autosub.editing import pending_groups, recover_times
from autosub.subtitles import Cue, Word, load_project, save_project, to_srt, validate


def test_split_draft_can_be_saved_but_not_exported():
    cues = [Cue(0, None, "測試"), Cue(None, 2, "English")]
    assert not validate(cues, 2, allow_pending=True)
    assert validate(cues, 2)
    with pytest.raises(ValueError, match="尚未填寫"):
        to_srt(cues, 2)
    raw = save_project(cues, 2, "audio", {})
    assert load_project(raw, "audio", 2)[0] == cues


def test_recovers_word_boundaries_and_preserves_silence():
    cues = [Cue(0, None, "繁體"), Cue(None, 3, "English")]
    result, count = recover_times(cues, [Word(0, 1, "繁體"), Word(1.5, 3, " English")])
    assert count == 1
    assert result == [Cue(0, 1, "繁體"), Cue(1.5, 3, "English")]
    assert cues[0].end is None  # input stays unchanged


def test_multiple_splits_in_one_region():
    cues = [Cue(0, None, "一"), Cue(None, None, "二"), Cue(None, 3, "三")]
    assert pending_groups(cues) == [(0, 2)]
    result, count = recover_times(cues, [Word(i,i+1,t) for i,t in enumerate("一二三")])
    assert count == 2
    assert not validate(result, 3)


def test_does_not_overwrite_manual_time_or_create_overlap():
    cues = [Cue(0, 1.2, "一"), Cue(None, 3, "二")]
    result, count = recover_times(cues, [Word(0,1,"一"), Word(1.5,3,"二")])
    assert result[0].end == 1.2
    assert result[1].start == 1.5
    assert count == 1
    assert recover_times(cues, [Word(0,1,"一"), Word(1.1,3,"二")])[1] == 0


@pytest.mark.parametrize("words", [[Word(0,3,"一二")], [Word(0,1,"錯"), Word(1,3,"字")]])
def test_uncertain_or_inside_word_split_stays_blank(words):
    cues = [Cue(0,None,"一"), Cue(None,3,"二")]
    result, count = recover_times(cues, words)
    assert result == cues
    assert count == 0


def test_ignores_punctuation_spacing_case_for_matching():
    cues = [Cue(0,None,"測試，"), Cue(None,3,"ESP32")]
    result, count = recover_times(cues, [Word(0,1,"測試"),Word(1,3," es p 32")])
    assert count == 1


def test_pending_draft_still_validates_known_times_and_text():
    assert validate([Cue(0,2,"一"), Cue(None,1,"二")], 3, allow_pending=True)
    assert validate([Cue(0,None,"一\n\n二")], 3, allow_pending=True)
    assert validate([Cue(float("nan"),None,"一")], 3, allow_pending=True)


def test_partially_filled_multiple_splits_share_one_region():
    cues = [Cue(0,None,"一"), Cue(1,None,"二"), Cue(None,3,"三")]
    assert pending_groups(cues) == [(0,2)]
    result, count = recover_times(cues, [Word(i,i+1,t) for i,t in enumerate("一二三")])
    assert count == 2
    assert result[1].start == 1
