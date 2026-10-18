# Auto Sub — 本機繁中字幕工具

Windows 本機音訊轉 SRT 工具（v0.1.0 原始碼版）。支援單一 MP3 / WAV / M4A、最長 5 分鐘、最大 100 MB。繁體中文為主，保留英文原文及口語，不翻譯、不潤飾、不辨識講者。無需 API key 或 ChatGPT 訂閱。

## 安裝與啟動

完整步驟與疑難排解見 **[Windows 安裝指南](docs/INSTALL_WINDOWS.md)**。

1. 安裝官方 **Python 3.12（64-bit）**；這是已驗證版本。
2. 從 GitHub 的 **Code → Download ZIP** 取得原始碼，或下載提供的 source ZIP，完整解壓縮到可寫入資料夾。
3. CPU 版：雙擊 **setup.bat**。NVIDIA GPU 版：在專案資料夾開啟 PowerShell 執行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Gpu
```

4. 安裝成功後雙擊 **start.bat**，開啟啟動視窗顯示的本機網址（通常為 `http://127.0.0.1:8501`）。CPU 版選 CPU／small；GPU 版可先選 NVIDIA GPU／turbo。
5. 第一次辨識會另行下載模型到 `models`，不要先勾離線選項。關閉前儲存專案 JSON；停止服務按啟動視窗的 Ctrl+C。

套件不包含 Python、虛擬環境、NVIDIA 函式庫或模型。GPU 套件下載超過 1 GB，turbo 模型另約 1.6 GB。安裝腳本只在資料夾內建立環境，使用已測試版本作約束，不自動安裝未選用的 GPU／測試套件。

亦可執行 `powershell -ExecutionPolicy Bypass -File .\start.ps1`。啟動器綁定 `127.0.0.1`，只供本機操作。`Bypass` 只針對該次 PowerShell 程序，不永久變更系統執行原則。這個版本不是獨立 EXE。

### NVIDIA GPU（選用）

faster-whisper / CTranslate2 需要相容的 NVIDIA driver、CUDA 12 cuBLAS 與 cuDNN 9 for CUDA 12 執行函式庫，且 DLL 必須在 PATH。`nvidia-smi` 顯示的 CUDA 版本代表 driver 能力，不能據此認定所需 DLL 已安裝。參照 [faster-whisper GPU requirements](https://github.com/SYSTRAN/faster-whisper#gpu)。未安裝完成時請先選 CPU。

Windows 可在虛擬環境安裝 NVIDIA 官方 wheels（下載約 1 GB 以上）：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[gpu]"
```

或執行 `powershell -ExecutionPolicy Bypass -File .\install-gpu.ps1`。程式會尋找虛擬環境內的 NVIDIA DLL，僅調整目前程序的 DLL 搜尋路徑，不更改系統 PATH。

CPU 預設 `small` INT8；GPU 暫以 `turbo` FP16 作為初始選項，可選 `large-v3` 比較。此選擇尚未由本專案的繁中測試確認。切換模型時只快取一個模型參照，不同時執行多個辨識工作。

## 使用

1. 選擇音檔與運算裝置、模型。開始辨識旁的齒輪圖示可調整語言、主題背景、專有名詞、輸出標點、字幕密度與進階辨識設定；每項旁的問號可懸浮查看詳細說明。辨識與斷句設定套用於下一次辨識，不會立即重排已編輯的字幕；輸出標點立即更新預覽與 SRT。
2. 按「開始辨識」。首次下載模型可能花較久時間；完成後快取於專案的 `models` 資料夾，可用 `AUTO_SUB_MODEL_DIR` 改位置。
3. 在「編輯字幕」內播放音訊，表格依起訖時間反白目前字幕。點字幕文字或編號可跳至該句開始時間，保留原本播放／暫停狀態；點時間欄或微調按鈕不會跳轉。每個時間欄都有 `-0.3 / -0.1 / +0.1 / +0.3` 秒按鈕，也可直接輸入秒數。
4. 按「同步音訊」啟用表格跟隨；進度列不在可見範圍時只捲動表格，不拉動整頁。預設關閉，自行捲動表格會關閉跟隨；再次點按即可恢復。反白與點句跳轉不受此開關影響。
5. 文字欄游標放在句中按「拆句」，新邊界的兩個時間先留白；游標在句首才啟用「向前合併」（需有上一句），在句尾才啟用「向後合併」（需有下一句）。選取一段文字時不啟用拆併句。可使用「復原」撤回近期修改。
   點選字幕文字、編號或時間欄後，工具列會顯示已選取的句號；按「刪除句子」可移除該列，按「復原」一次即可撤回。沒有選取列時停用刪除。刪除不裁切音訊、不平移其他句子的時間；允許刪到空表格並復原。專案儲存刪除後的編輯結果，原始辨識資料仍保留供追溯。
6. 完成文字調整後按「自動辨識斷句時間」，或自行填入空白時間。修改自動同步，等待表格下方顯示「已同步」後，再下載 SRT 或儲存專案 JSON。專案包含原始辨識片段、word timestamps、模型、耗時、辨識設定與編輯後字幕。
7. 重新啟動後，先選擇相同原始音檔，再開啟專案 JSON。專案使用 SHA-256 確認音檔相符，不內嵌音訊。新版專案格式 v2 可保存空白時間，也相容讀取 v1。專案內保留當次辨識設定供追溯，載入專案不覆蓋目前設定選單。

模型檔案完整下載後，可勾選「僅使用已下載模型」離線執行。音訊不會送至 OpenAI，不需要 API key 或訂閱。首次模型下載會連到 Hugging Face；Streamlit 使用統計已停用。

### 自動辨識斷句時間

優先將修改後文字對上原始 word timestamps；無法對上時才重新辨識有缺漏時間的音訊區間。只有文字正規化後完整一致、且斷點位於實際 word 邊界時才填時間，不按字數比例內插。保留已手填的時間與實際停頓空隙。無法匹配、切在同一個 word 內或結果會造成重疊時，時間維持空白並提示手填。

自動補時只更新時間，不改寫使用者的文字。目前仍使用 faster-whisper，**未接入 WhisperX 或額外強制對齊模型**。時間空白的草稿可保存專案，不能匯出 SRT；空白時間的列也無法精確播放反白。

### 辨識與字幕偏好

齒輪選單提供中文／英文／自動語言、主題與術語提示，以及短句／標準／長句／自訂密度。可分別設定每行字寬、行數、停頓、最長時間與標點拆句方式。自訂排版只影響辨識後的字幕分組。

進階選單可調候選搜尋、自動重試或固定取樣變化、前段上下文、語音偵測及其門檻、靜音與前後保留量，以及重複／低信心／無人聲判定。所有選項實際傳入 faster-whisper；自動重試時固定取樣值不生效，停用語音偵測時其細項不生效。逐詞時間為字幕功能的必要條件，固定開啟。術語與背景只是提示，不是保證或強制取代；調高數值不代表更準。可按「恢復預設設定」。

設定在目前瀏覽器工作階段中保留，沒有自動寫入全域偏好檔。局部重新辨識也使用當前設定；主轉錄的設定快照保留於專案 metadata，不因局部補時而改寫。

### 輸出標點方式

齒輪選單可選「保留標點」「移除標點」「標點改成空格」。例如 `今天測試，明天再看。` 可輸出為原文、`今天測試明天再看` 或 `今天測試 明天再看`。選擇立即套用至預覽與下載 SRT，無須重新辨識；表格、原始辨識資料與起訖時間保持原樣，斷句也不會重算。

移除是在輸出時逐字處理 Unicode 標點類別，並不是要求 Whisper 不產生標點。表格保留含標點原文是正常行為；編輯區上方會明示目前輸出模式，移除／空格模式會自動展開「預覽字幕」。請區分「標點斷句方式」（控制在哪裡切句）與「輸出標點方式」（控制 SRT 文字）。`+`、`=`、`~` 等數學符號不屬於此規則移除的標點。

移除／空格模式處理句讀、引號與括號等標點，但保留常見的小數、數字分隔、百分比、英文單字內符號與網址格式，例如 `3.3V`、`Wi-Fi`、`don't`、`C++`、`C#`。這是規則式處理，特殊術語仍請檢查預覽。連續空格會合併、非空白換行保留；純標點而變成空白的字幕會在 SRT 略過並重新編號。專案 JSON 保留原文，並於 metadata 的 `export_settings` 記錄此次輸出選擇；載入專案不覆蓋目前選單設定。

## 字幕與語言限制

- 依 word timestamps、停頓、標點、最多兩行與字寬切分；中文寬度計為 1、英數約 0.5，預設每行 20。此為近似顯示寬度，非語意模型。
- 不拆開英文單字。若模型只給了一個很長的 token 或片段，可能超過排版建議，介面會提示；不以平均分配方式捏造時間。
- 使用中文辨識提示及 transcription 模式。中英夾雜、英文專有名詞、語助詞與時間精度仍可能出錯，需要人工核對。
- OpenCC `s2t` 做繁體字形轉換，不主動改為台灣用語。
- 時間戳記是模型估計，尚未加入額外 forced alignment 或波形拖曳介面。
- 匯出阻擋時間重疊、負數、超出音檔、空白文字及 SRT 空白分隔行等錯誤；排版超寬僅提示，不阻擋匯出。
- 請先下載專案再關閉頁面或切換音檔；工作階段不自動寫入磁碟。

## 驗證

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Dev
.\.venv\Scripts\python.exe -m pytest -q
```

人工驗收：相同音檔分別測試 turbo 與 large-v3，至少包含純中文、中英混合、明顯停頓的樣本。比較漏字、誤字、字幕重複、時間起訖及實際處理秒數。命令列工具將模型取得（包含可能的快取／下載）與辨識時間分開記錄；公平比較時先完成下載，分別記錄冷啟動與暖啟動。

也可用命令列比較，輸出 SRT 與專案 JSON 至 `outputs`：

```powershell
.\.venv\Scripts\python.exe tools/benchmark.py path/to/audio.wav --model turbo --device cuda
.\.venv\Scripts\python.exe tools/benchmark.py path/to/audio.wav --model large-v3 --device cuda
```

目前提供原始碼與啟動腳本，尚未提供 Windows 安裝包。開發機已通過 45 項單元／介面載入測試及實際 Edge 瀏覽器操作測試；真人旁白品質與模型比較仍待驗證。詳細結果與限制見 [VALIDATION.md](VALIDATION.md)。`requirements-tested.txt` 記錄此 Windows 測試環境（包含 GPU、Playwright 與測試套件）的版本。

瀏覽器測試需安裝 Edge、啟動本機服務，並準備 `outputs/smoke-bilingual.wav`（開發時以 Windows 語音合成產生，不含於 Git 儲存庫）：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ui-test]"
.\.venv\Scripts\python.exe tools/ui_smoke.py
```

## 授權

本專案採 MIT License。Whisper 模型、faster-whisper 與其他依賴的授權及上游連結見 [THIRD_PARTY.md](THIRD_PARTY.md)。發布安裝包前需納入實際打包版本的第三方授權文字。

## 重建原始碼套件

```powershell
.\.venv\Scripts\python.exe tools/package_source.py
```

輸出 `dist/auto-sub-local-0.1.0-source.zip`、`SHA256SUMS.txt` 與來源檔案清單。採明確來源清單，只包含程式、測試、文件與啟動／安裝腳本；不包含音檔、專案 JSON、模型、虛擬環境、快取或本機測試輸出。`requirements-tested.txt` 是版本約束參考，請勿把它當成每位使用者都要安裝的完整清單。
