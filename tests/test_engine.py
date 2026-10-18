import io
import wave
from types import SimpleNamespace

import pytest

from autosub.engine import decode_audio, transcribe
from autosub.subtitles import validate


def wav_bytes(seconds):
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * int(16000 * seconds))
    return output.getvalue()


def test_decodes_wav_and_preserves_duration():
    audio, duration = decode_audio(wav_bytes(1.25), "test.wav")
    assert duration == 1.25
    assert audio.dtype.name == "float32"
    assert len(audio) == 20000


def test_rejects_overlong_audio():
    with pytest.raises(ValueError, match="5 分鐘"):
        decode_audio(wav_bytes(300.1), "long.wav")


def test_accepts_exactly_five_minutes():
    audio, duration = decode_audio(wav_bytes(300), "limit.wav")
    assert duration == 300


@pytest.mark.parametrize("extension,container_format,codec", [
    ("mp3", "mp3", "libmp3lame"), ("m4a", "ipod", "aac")])
def test_decodes_supported_compressed_formats(extension, container_format, codec):
    import av
    import numpy as np

    output = io.BytesIO()
    with av.open(output, "w", format=container_format) as container:
        stream = container.add_stream(codec, rate=16000)
        stream.layout = "mono"
        frame = av.AudioFrame.from_ndarray(np.zeros((1, 16000), dtype="float32"),
                                           format="fltp", layout="mono")
        frame.sample_rate = 16000
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    audio, duration = decode_audio(output.getvalue(), f"sample.{extension}")
    assert abs(duration - 1.0) < 0.1
    assert len(audio) > 0


@pytest.mark.parametrize("raw,name", [(b"", "empty.wav"), (b"not audio", "bad.wav"), (b"x", "video.mp4")])
def test_rejects_invalid_inputs(raw, name):
    with pytest.raises(Exception):
        decode_audio(raw, name)


def test_transcription_keeps_english_and_converts_traditional():
    import numpy as np

    class FakeModel:
        def transcribe(self, audio, **options):
            assert options["task"] == "transcribe"
            assert options["word_timestamps"] is True
            words = [SimpleNamespace(start=0.2, end=0.6, word="测试"),
                     SimpleNamespace(start=0.6, end=1.2, word=" ESP32"),
                     SimpleNamespace(start=1.2, end=1.2, word="。")]
            segment = SimpleNamespace(start=0.2, end=1.2, text="测试 ESP32。", words=words)
            return iter([segment]), SimpleNamespace(language="zh")

    cues, metadata = transcribe(FakeModel(), np.zeros(32000, dtype="float32"), "turbo", "cpu")
    assert cues[0].text == "測試 ESP32。"
    assert not validate(cues, 2)
    assert metadata["raw_segments"][0]["text"] == "测试 ESP32。"
