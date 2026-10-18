# Validation snapshot — 2026-10-18

## Environment

- Windows, Intel i5-12400F, NVIDIA RTX 3060 12 GB, 16 GB system RAM.
- Python 3.12.15, faster-whisper 1.2.1, CTranslate2 4.8.3, Streamlit 1.66.0.
- NVIDIA driver 610.88. CUDA 12 runtime / cuBLAS and cuDNN 9 installed as optional Python wheels inside `.venv`.
- Exact installed versions: `requirements-tested.txt` (includes GPU and test dependencies).

## Automated checks

`python -m pytest -q`: **46 passed**, including the source-package allowlist check.

Covers real WAV / MP3 / M4A decoding; exactly 300 seconds accepted and overlong input rejected; bilingual subtitle grouping; English word wrapping; SRT millisecond formatting; invalid / overlapping times; project round-trip and audio identity; Traditional Chinese conversion using a mock recognizer; Streamlit initial page and subtitle editing / export rendering.

Additional cases cover drafts with null start/end times, exact word-boundary timing recovery, multi-split regions, partially hand-filled times, refusing uncertain / inside-word boundaries, preserving user times, and validating known times even in unfinished drafts.

Preference checks cover actual forwarding of language, context, hotwords, sampling, context carry-over, VAD and confidence options to the model call; recording settings in metadata; layout effects; density presets, custom values, and restoring defaults.

Output-format checks cover keep/remove/spaces modes, common technical punctuation and URLs beside Chinese text, whitespace and manual line breaks, skipping punctuation-only output, contiguous SRT numbering, and unchanged source cues and timestamps.

## Real browser editor checks

`python tools/ui_smoke.py` passed in headless Microsoft Edge against the real local Streamlit server and GPU transcription. Checks include:

- Ordered model selection and removal of obsolete jump/play controls.
- Text-cursor splitting, null internal times, and merge availability only at text edges.
- Blocking SRT export while allowing JSON draft download with unresolved times.
- Automatic word-based timing recovery, numeric increment/decrement controls.
- Real audio playback highlighting the correct row and maintaining playback position during edits.
- Text containing an unspoken annotation: automatic recovery leaves times blank and requests manual input; manually filling them enables SRT export.
- No browser JavaScript page errors. Screenshot: `outputs/editor-ui.png` (not committed).
- Icon-only preferences beside the start button, real hover help, and exported settings matching the chosen terminology hints. Settings screenshot: `outputs/settings-ui.png`.
- Clicking a cue seeks the real audio while preserving both playing and paused states.
- A separate 20-cue fixture verifies following an offscreen cue, remaining enabled after programmatic scrolling, cancelling on manual wheel scrolling, staying put when disabled, and resuming on demand.
- Separate backward/forward merge buttons enforce their respective cursor and neighbor constraints.

`python tools/punctuation_smoke.py` also passed in Edge: changed all three output modes after loading an existing project without re-transcription; checked preview/download agreement, unchanged editor text and SRT timestamps, and the saved export preference in project JSON.

`python tools/deletion_smoke.py` passed: deletion is disabled without a selected cue; a time-field click selects the correct row; deleting preserves remaining cues, their timestamps and audio position/pause state; JSON saves deletion; one undo restores the complete deleted row; deleting all rows disables SRT and undo restores the last row. It also verifies that the active output mode is visible and removal opens the processed preview. Undo now ignores duplicate focus-only snapshots so programmatic refocusing does not consume the first undo click.

The automatic timing feature uses existing word timestamps, with local faster-whisper re-transcription as fallback. It does not include WhisperX forced alignment and does not interpolate positions inside a word.

## Real inference smoke test

Generated a 17.248-second bilingual WAV locally using Windows Microsoft Hanhan and Zira speech synthesis voices. Ran `tools/benchmark.py` using the same downloaded turbo model, without network during inference.

| Device / compute | Model access | Transcription | Cues |
| --- | ---: | ---: | ---: |
| CPU / INT8 | 3.457 s | 6.489 s | 4 |
| RTX 3060 / FP16 | 2.306 s | 0.951 s | 4 |

Both runs successfully wrote SRT and editable project JSON. Model-access timing excludes first download. These are single short synthetic-audio runs, not quality benchmarks or forecasts for five-minute human recordings.

The GPU output preserved English, but rendered the spoken term `ESP32` as `ES P 32` and used an ASCII comma. The first output placed a line break inside a Chinese word; wrapping was subsequently adjusted to prefer a nearby clause boundary and regression-tested. Arbitrary Chinese word boundaries still require manual layout review. No numerical transcription-accuracy claim is made.

## Service

Streamlit started on `127.0.0.1:8501`; `/_stcore/health` returned `ok`.

## Source distribution installation check

Extracted the v0.1.0 source ZIP to a separate folder on the same Windows host. Ran `install.ps1 -Dev -PythonExecutable <Python 3.12.15 path>` to create a new virtual environment and download dependencies, without using the development environment's packages. Dependency imports succeeded and all **46 tests passed** in the extracted copy. This checks the CPU installation path; it is not a clean Windows machine or a fresh GPU dependency installation.

The package uses an explicit source allowlist and includes a per-file SHA-256 manifest and archive checksum. Audio, transcription outputs, models, virtual environments and local caches are excluded.

## Still to validate / deliver

- Human-recorded pure Chinese, mixed-language and pause-heavy narration.
- large-v3 versus turbo quality comparison on those recordings; turbo is only a provisional default.
- Fresh Windows installation and machines with CPU only / limited memory.
- Standalone executable packaging and complete bundled third-party notices (the current distribution is source only).
- Fine word alignment and waveform-based timeline editing are outside this first version.
