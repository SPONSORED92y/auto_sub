"""Human-readable preferences. Streamlit help icons provide hover tooltips."""
import streamlit as st

from .settings import RecognitionSettings

PREFIX = "recognition_"
LANGUAGES = {"中文為主": "zh", "英文": "en", "自動判斷": None}
PUNCTUATION = {"只在句尾": "sentence", "較長的逗號句也拆開": "standard", "遇到逗號也拆開": "frequent"}
OUTPUT_PUNCTUATION = {"保留標點": "keep", "移除標點": "remove", "標點改成空格": "spaces"}
PRESETS = {"短句": (18, 1, 0.3, 4.0, "遇到逗號也拆開"),
           "標準": (20, 2, 0.6, 6.0, "較長的逗號句也拆開"),
           "長句": (22, 2, 1.0, 8.0, "只在句尾")}


def set_preset():
    values = PRESETS.get(st.session_state[PREFIX + "density"])
    if values:
        for name, value in zip(("line_width", "max_lines", "pause", "max_duration", "punctuation"), values):
            st.session_state[PREFIX + name] = value


def custom_layout():
    st.session_state[PREFIX + "density"] = "自訂"


def reset_preferences():
    for key in list(st.session_state):
        if key.startswith(PREFIX):
            del st.session_state[key]


def preferences() -> RecognitionSettings:
    """Call inside a popover on every run, so widget state stays mounted."""
    st.markdown("**辨識與字幕設定**")
    st.caption("辨識與斷句設定套用於下一次辨識；輸出標點立即套用至預覽與 SRT。每項旁的問號可懸浮查看說明。")
    language = st.selectbox("音檔的主要語言", list(LANGUAGES), key=PREFIX+"language",
        help="中文為主適合目前的中英夾雜旁白，英文模式適合全英文音檔。自動判斷由模型偵測主要語言，並不保證每次切換語言都能正確辨識；三種模式都不翻譯。")
    context = st.text_area("提供主題與背景提示", key=PREFIX+"context", max_chars=2000,
        help="用簡短文字描述主題或提供詞彙範例，例如：這是一段類比電路設計教學。提示會影響辨識方向，不是強制指令，也不是完整旁白稿對齊。過長或不相關的提示可能增加誤辨識。")
    hotwords = st.text_input("提供專有名詞提示", key=PREFIX+"hotwords", max_chars=2000,
        placeholder="例如 ESP32, Arduino, MOSFET",
        help="輸入可能出現的人名、產品名或術語，以逗號分隔。這是辨識提示，不是強制取代字典；無法保證拼字一定正確。請只填音訊中可能出現的詞。")
    output_punctuation = st.selectbox("輸出標點方式", list(OUTPUT_PUNCTUATION),
        key=PREFIX+"output_punctuation",
        help="保留標點：輸出原文。移除標點：刪除句讀與括號引號，不另外加空格。標點改成空格：以空格取代並合併連續空格。保留小數、數字分隔、英文單字內符號及網址等常見格式；這是規則處理，仍可檢查預覽。只改 SRT 與預覽，不改表格、斷句或時間，無須重新辨識。純標點且處理後為空白的字幕會略過。")
    st.selectbox("字幕密度", ["短句", "標準", "長句", "自訂"], index=1,
        key=PREFIX+"density", on_change=set_preset,
        help="短句：單行、較短時間、短停頓與逗號也拆句。標準：雙行與中等斷句。長句：容許較長字幕。調整下方細項會切換成自訂。這些是辨識後的排版規則。")
    layout = dict(on_change=custom_layout)
    line_width = st.number_input("每行最多中文字寬", 10, 40, 20, key=PREFIX+"line_width",
        help="一個中文字約計為 1，英數字約 0.5。較小會產生更多短字幕；英文單字不硬拆。長詞可能超寬並顯示提示。", **layout)
    max_lines = st.selectbox("每句最多行數", [1, 2], index=1, key=PREFIX+"max_lines",
        help="設定一筆字幕最多使用一行或兩行。文字過長時，優先依已有詞時間分成不同字幕；不會憑字數捏造斷點。", **layout)
    pause = st.number_input("停頓多久就拆句（秒）", 0.1, 3.0, 0.6, step=0.1, key=PREFIX+"pause",
        help="相鄰詞之間的停頓達到此值，就換下一句字幕。較小通常斷句較多。這不會刪掉音訊，也不同於下方的語音偵測靜音門檻。", **layout)
    max_duration = st.number_input("每句最長顯示時間（秒）", 1.0, 15.0, 6.0, step=0.5, key=PREFIX+"max_duration",
        help="一筆字幕超過此長度時，嘗試在詞邊界切開。模型只提供一個長詞時可能超過此值，仍需手動校正。", **layout)
    punctuation = st.selectbox("標點斷句方式", list(PUNCTUATION), index=1, key=PREFIX+"punctuation",
        help="只在句尾：逗號不主動切句。較長的逗號句也拆開：達到一定長度才切。遇到逗號也拆開：斷句較細。停頓、長度與行數限制仍會生效。", **layout)

    with st.expander("進階辨識設定"):
        beam = st.number_input("辨識候選搜尋範圍", 1, 10, 5, key=PREFIX+"beam_size",
            help="數字越大，解碼時保留更多候選，通常更耗時，但不保證更準。主要在取樣變化程度為零時使用；建議先維持 5。")
        retry = st.checkbox("結果不理想時自動嘗試其他候選", True, key=PREFIX+"automatic_retry",
            help="啟用時，依序使用由穩定到較多變化的取樣方式重試未通過門檻的片段。停用後固定使用下方的變化程度；不是整段音檔無限重試。")
        temperature = st.slider("候選文字的變化程度", 0.0, 1.0, 0.0, 0.1,
            disabled=retry, key=PREFIX+"temperature",
            help="零表示採用較穩定的候選搜尋；大於零會進行取樣，結果可能更不固定。較高不代表較準；自動重試啟用時由程式決定，不使用此固定值。")
        previous = st.checkbox("參考前段辨識文字", True, key=PREFIX+"previous_context",
            help="將前段辨識結果提供給後段作為上下文，可能改善連貫性，也可能延續前段錯字或重複內容。若經常出現重複字幕，可以嘗試關閉。")
        vad = st.checkbox("先偵測語音再辨識", True, key=PREFIX+"vad_filter",
            help="先找出有說話的區域，減少對靜音進行辨識。門檻過高可能漏掉輕聲；這不是降噪功能。")
        threshold = st.slider("判定為語音的嚴格程度", 0.1, 0.9, 0.5, 0.05,
            disabled=not vad, key=PREFIX+"vad_threshold",
            help="較低較容易將音訊判為語音，可能保留輕聲也可能納入噪音；較高更嚴格，可能漏字。建議先用 0.5。")
        silence = st.number_input("語音片段之間的靜音門檻（毫秒）", 100, 3000, 2000, step=100,
            disabled=not vad, key=PREFIX+"silence_ms",
            help="語音偵測用此長度的靜音分開片段。較小會形成較多辨識片段；它不直接決定最後 SRT 的斷句。1000 毫秒等於 1 秒。")
        padding = st.number_input("語音前後額外保留時間（毫秒）", 0, 1000, 400, step=50,
            disabled=not vad, key=PREFIX+"padding_ms",
            help="在偵測到的語音前後多保留一些聲音，降低句首句尾被截掉的機會。設太大會連同更多靜音一起處理。")
        compression = st.number_input("重複文字的容許門檻", 1.0, 5.0, 2.4, step=0.1,
            key=PREFIX+"compression_threshold",
            help="使用文字壓縮比判斷結果是否過度重複。較低更容易判定失敗並嘗試其他候選；正常重複內容也可能被誤判。建議先維持 2.4。")
        confidence = st.number_input("辨識結果的可信度門檻", -5.0, 0.0, -1.0, step=0.1,
            key=PREFIX+"confidence_threshold",
            help="模型平均對數機率低於此值時，結果視為低信心。越接近零越嚴格，可能更常重試；這不是正確率百分比。建議先維持 -1。")
        no_speech = st.slider("判定為無人聲的門檻", 0.0, 1.0, 0.6, 0.05,
            key=PREFIX+"no_speech_threshold",
            help="搭配低信心判定，決定是否把片段視為無人聲並略過。較低較容易略過，可能漏掉輕聲；較高可能保留靜音中的誤辨識。建議先維持 0.6。")
        st.checkbox("取得逐詞時間（字幕編輯必需）", True, disabled=True,
            help="播放反白、拆句與自動補時間都需要逐詞時間，因此此工具固定啟用。時間仍是模型估計，不代表逐字精準。")
    st.button("恢復預設設定", on_click=reset_preferences)
    return RecognitionSettings(language=LANGUAGES[language], context=context, hotwords=hotwords,
        beam_size=beam, automatic_retry=retry, temperature=temperature, previous_context=previous,
        vad_filter=vad, vad_threshold=threshold, silence_ms=silence, padding_ms=padding,
        compression_threshold=compression, confidence_threshold=confidence, no_speech_threshold=no_speech,
        line_width=line_width, max_lines=max_lines, pause=pause, max_duration=max_duration,
        punctuation=PUNCTUATION[punctuation], output_punctuation=OUTPUT_PUNCTUATION[output_punctuation])
