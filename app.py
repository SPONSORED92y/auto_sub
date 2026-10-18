"""Run with: streamlit run app.py"""
from pathlib import Path
import time
import streamlit as st
from autosub import engine
from autosub.editing import recover_times
from autosub.editor import subtitle_editor
from autosub.settings_ui import preferences
from autosub.subtitles import Cue, Word, load_project, save_project, to_srt, validate, width

st.set_page_config(page_title="Auto Sub 本機字幕", page_icon="🎧", layout="wide")
st.title("Auto Sub 本機字幕")
st.caption("5 分鐘內單人旁白 · 繁體中文與英文原文 · 音訊在本機處理")

@st.cache_resource(max_entries=1)
def get_model(name, device, offline):
    return engine.load_model(name, device, offline)

@st.cache_data(max_entries=1, show_spinner=False)
def decode(raw, name):
    return engine.decode_audio(raw, name)

with st.sidebar:
    st.header("辨識設定")
    available_gpu = engine.gpu_count() > 0
    device_label = st.selectbox("運算裝置", ["NVIDIA GPU", "CPU"] if available_gpu else ["CPU"])
    device = "cuda" if device_label == "NVIDIA GPU" else "cpu"
    names = list(engine.MODEL_NAMES)
    model_name = st.selectbox("模型（由輕到強）", names, index=2 if device == "cuda" else 0)
    st.caption("small → medium → turbo → large-v3。turbo 為加速版本，此排序不是所有音檔的準確度保證。")
    offline = st.checkbox("僅使用已下載模型（離線）")
    st.caption(f"模型快取：{engine.MODEL_DIR}")
    st.caption("目前使用 faster-whisper。首次使用模型需要下載；CPU 建議先用 small。")
    if st.button("釋放模型快取"):
        get_model.clear()
        st.success("已清除程式的模型快取參照。")

uploaded = st.file_uploader("選擇或拖曳音檔（最長 5 分鐘、100 MB）", type=["mp3", "wav", "m4a"])
if uploaded is None:
    st.info("請先選擇音檔。模型只在按下「開始辨識」後載入。")
    st.stop()

raw = uploaded.getvalue()
digest = engine.audio_hash(raw)
mime = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4"}[Path(uploaded.name).suffix.lower()]
try:
    with st.spinner("檢查音檔…"):
        audio, duration = decode(raw, uploaded.name)
except Exception as exc:
    st.error(f"無法讀取音檔：{exc}")
    st.stop()

if st.session_state.get("digest") != digest:
    for key in ("cues", "metadata", "project_upload", "last_event", "notice"):
        st.session_state.pop(key, None)
    st.session_state.digest = digest
    st.session_state.revision = st.session_state.get("revision", 0) + 1

st.write(f"音檔：{uploaded.name} ｜ 長度：{duration:.2f} 秒")
if "cues" not in st.session_state:
    st.audio(raw, format=mime)

with st.container(horizontal=True, gap="small", vertical_alignment="center"):
    start = st.button("開始辨識", type="primary")
    with st.popover("", icon=":material/settings:", help="辨識與字幕設定"):
        settings = preferences()
line_width = settings.line_width

if start:
    try:
        with st.spinner("載入模型；首次使用會下載，請稍候…"):
            started = time.perf_counter()
            model = get_model(model_name, device, offline)
            load_seconds = time.perf_counter() - started
        with st.spinner("本機辨識中…"):
            cues, metadata = engine.transcribe(model, audio, model_name, device, settings=settings)
        metadata.update(model_access_seconds=round(load_seconds, 3), line_width=line_width)
        st.session_state.cues = cues
        st.session_state.metadata = metadata
        st.session_state.revision += 1
        st.rerun()
    except Exception as exc:
        st.error(f"辨識失敗：{exc}")
        st.info("GPU 錯誤請確認 CUDA／cuDNN 套件，或改選 CPU；原有字幕會保留。")

with st.expander("開啟已儲存專案"):
    project_file = st.file_uploader("選擇專案 JSON，並同時載入原始音檔", type=["json"], key="project_upload")
    if st.button("載入專案", disabled=project_file is None):
        try:
            if project_file.size > 10 * 1024 * 1024:
                raise ValueError("專案檔超過 10 MB。")
            cues, metadata = load_project(project_file.getvalue().decode("utf-8-sig"), digest, duration)
            st.session_state.cues = cues
            st.session_state.metadata = metadata
            st.session_state.revision += 1
            st.rerun()
        except Exception as exc:
            st.error(f"無法載入專案：{exc}")

if "cues" not in st.session_state:
    st.stop()

metadata = st.session_state.metadata
st.caption(f"模型：{metadata.get('model', '未知')} ｜ 裝置：{metadata.get('device', '未知')} ｜ "
           f"辨識耗時：{metadata.get('transcription_seconds', '未知')} 秒")
st.subheader("編輯字幕")
output_label = {"keep":"保留標點", "remove":"移除標點", "spaces":"標點改成空格"}[settings.output_punctuation]
st.info(f"目前 SRT 輸出：{output_label}。表格保留原文；處理後的文字請看下方「預覽字幕」。可從齒輪選單的「輸出標點方式」切換。")
if st.session_state.get("notice"):
    st.info(st.session_state.notice)

event = subtitle_editor(st.session_state.cues, raw, mime, digest, duration, st.session_state.revision)
if (isinstance(event, dict) and event.get("event_id") != st.session_state.get("last_event")
        and event.get("revision") == st.session_state.revision):
    st.session_state.last_event = event.get("event_id")
    try:
        rows = event.get("cues")
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError("字幕資料格式或數量不合法。")
        cues = [Cue(**row) for row in rows]
        if any(not isinstance(c.text, str) for c in cues):
            raise ValueError("字幕文字格式不合法。")
        st.session_state.cues = cues
        st.session_state.pop("notice", None)
        if event.get("action") == "auto":
            words = [Word(**w) for w in metadata.get("words", [])]
            cues, recovered = recover_times(cues, words)
            if any(c.start is None or c.end is None for c in cues):
                try:
                    with st.spinner("重新辨識待補時間的音訊片段…"):
                        model = get_model(model_name, device, offline)
                        cues, count = engine.recognize_boundaries(model, audio, cues, model_name, device, settings=settings)
                        recovered += count
                except Exception as exc:
                    st.session_state.notice = f"局部辨識失敗：{exc}。已取得的時間會保留，其餘請手動填寫。"
            st.session_state.cues = cues
            missing = sum(c.start is None for c in cues) + sum(c.end is None for c in cues)
            summary = f"已補上 {recovered} 處斷句。" + (f"仍有 {missing} 個起訖時間無法可靠辨識，請手動填寫。" if missing else "所有斷句時間已填寫。")
            st.session_state.notice = summary + " " + st.session_state.get("notice", "")
            st.session_state.revision += 1
    except Exception as exc:
        st.session_state.notice = f"編輯未完成：{exc}"
        st.session_state.revision += 1
    st.rerun()

cues = st.session_state.cues
errors = validate(cues, duration)
if any(c.start is None or c.end is None for c in cues):
    st.warning("部分斷句時間尚未填寫：可以先儲存專案，補齊時間後才能匯出 SRT。")
for error in errors:
    if "尚未填寫" not in error:
        st.error(error)
layout_exceptions = [i for i, c in enumerate(cues, 1)
                     if len(c.text.splitlines()) > settings.max_lines or any(width(line) > line_width for line in c.text.splitlines())]
if layout_exceptions:
    st.warning(f"第 {', '.join(map(str, layout_exceptions[:20]))} 句超過排版建議，可手動調整。")

stem = Path(uploaded.name).stem
srt = to_srt(cues, duration, punctuation_mode=settings.output_punctuation) if not errors else ""
if cues and not errors and not srt:
    st.warning("目前輸出標點方式下沒有可輸出的文字，請檢查字幕內容或改為保留標點。")
export_metadata = {**metadata, "export_settings": {"punctuation": settings.output_punctuation}}
left, right = st.columns(2)
with left:
    st.download_button("下載 SRT", srt,
                       file_name=f"{stem}.srt", mime="application/x-subrip", disabled=bool(errors) or not srt)
with right:
    st.download_button("儲存專案 JSON", save_project(cues, duration, digest, export_metadata),
                       file_name=f"{stem}.autosub.json", mime="application/json",
                       disabled=bool(validate(cues, duration, allow_pending=True)))
with st.expander("預覽字幕", expanded=settings.output_punctuation != "keep"):
    if not errors:
        st.caption("此處與下載 SRT 使用相同的輸出標點方式；編輯表格保留原文。")
        st.code(srt, language="text")
