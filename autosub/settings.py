"""Recognition preferences and their mapping to faster-whisper options."""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RecognitionSettings:
    language: str | None = "zh"
    context: str = ""
    hotwords: str = ""
    beam_size: int = 5
    automatic_retry: bool = True
    temperature: float = 0.0
    previous_context: bool = True
    vad_filter: bool = True
    vad_threshold: float = 0.5
    silence_ms: int = 2000
    padding_ms: int = 400
    compression_threshold: float = 2.4
    confidence_threshold: float = -1.0
    no_speech_threshold: float = 0.6
    line_width: int = 20
    max_lines: int = 2
    pause: float = 0.6
    max_duration: float = 6.0
    punctuation: str = "standard"
    output_punctuation: str = "keep"

    def recognition_options(self) -> dict:
        prompt = "以下是旁白，請忠實轉錄並保留原文與口語；中文使用繁體字。"
        if self.context.strip():
            prompt += "\n" + self.context.strip()
        return dict(language=self.language, task="transcribe", beam_size=self.beam_size,
                    word_timestamps=True, initial_prompt=prompt, hotwords=self.hotwords.strip() or None,
                    temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0] if self.automatic_retry else self.temperature,
                    condition_on_previous_text=self.previous_context,
                    vad_filter=self.vad_filter,
                    vad_parameters={"threshold": self.vad_threshold,
                                    "min_silence_duration_ms": self.silence_ms,
                                    "speech_pad_ms": self.padding_ms},
                    compression_ratio_threshold=self.compression_threshold,
                    log_prob_threshold=self.confidence_threshold,
                    no_speech_threshold=self.no_speech_threshold)

    def layout_options(self) -> dict:
        return dict(line_width=self.line_width, max_lines=self.max_lines, pause=self.pause,
                    max_duration=self.max_duration, punctuation=self.punctuation)

    def to_dict(self) -> dict:
        return asdict(self)
