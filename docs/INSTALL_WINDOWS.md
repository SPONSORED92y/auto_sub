# Windows 安裝與啟動

此套件是 **v0.1.0 原始碼包**，不是免安裝 EXE。安裝腳本會在解壓縮資料夾建立 `.venv`，不必啟用虛擬環境，也不會修改系統 PATH。安裝程式依賴與首次下載模型需要網路；模型下載完成後可離線辨識。

## 1. 準備環境

- Windows 10／11、64-bit。建議 RAM 16 GB；8 GB／CPU 配置仍待更多實機驗證，先選 small。
- 安裝 [Python 3.12 Windows 64-bit](https://www.python.org/downloads/windows/)。安裝程式若提供 Python launcher 與 Add Python to PATH 選項，請勾選。**目前乾淨環境驗證使用 Python 3.12**；3.11／3.13 可嘗試，但沒有相同驗證範圍。
- NVIDIA GPU 加速為選用功能。開發機 RTX 3060 12 GB 已執行成功；其他 GPU 的速度與可用模型需實測。
- 無需 ChatGPT 訂閱、OpenAI API key 或付費帳戶。

開啟新的 PowerShell，確認 Python 可用：

```powershell
py install 3.12
py -3.12 --version
```

`py install` 是官方新版 Python install manager 的命令；已有 64-bit Python 3.12 可略過安裝，只確認版本。若舊版 launcher 不支援此命令，請從官方下載頁安裝新版 manager，或使用已安裝的 Python 完整路徑。參考 [Python Windows 官方說明](https://docs.python.org/3/using/windows.html)。

## 2. 下載與解壓縮

從有權限存取的 GitHub 儲存庫選 **Code → Download ZIP**，或使用提供的 `auto-sub-local-0.1.0-source.zip`。私人儲存庫須先登入獲授權的 GitHub 帳號。

將 ZIP 完整解壓縮到自己可寫入的資料夾，例如 `D:\Apps\auto_sub`。請勿直接在 ZIP 內執行，也不要放在 Program Files 等通常需要管理員權限的資料夾。進入能看見 `app.py`、`setup.bat`、`pyproject.toml` 的那一層。

## 3. 安裝：選 CPU 或 NVIDIA GPU

### CPU（較簡單，下載較少）

雙擊 **setup.bat**，等待顯示 `Installation complete`。亦可在專案資料夾開啟 PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

安裝完後，請在工具內選擇 **CPU／small**。即使程式偵測到 NVIDIA GPU，未裝 GPU 執行套件前仍請選 CPU。

### NVIDIA GPU（你的 RTX 3060 建議使用）

先安裝或更新 [NVIDIA 官方驅動程式](https://www.nvidia.com/Download/index.aspx)，在專案資料夾開啟 PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Gpu
```

這會安裝基礎套件及 NVIDIA CUDA 12／cuBLAS／cuDNN 9 執行函式庫，**下載超過 1 GB**，並占用額外磁碟空間。不需要為本工具另外安裝完整 CUDA 開發工具組；程式會從虛擬環境尋找所需 DLL。

已先安裝 CPU 版也可以執行相同 `-Gpu` 命令加入 GPU 支援，不需刪除原有環境。

也可在命令列使用 `setup.bat -Gpu`。若要指定已安裝的 Python：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Gpu -PythonExecutable 'C:\Path\To\Python312\python.exe'
```

`ExecutionPolicy Bypass` 僅套用該次程序，不永久變更 PowerShell 執行原則。無需以系統管理員身分執行。

## 4. 啟動與首次辨識

1. 雙擊 **start.bat**；保留啟動的命令列視窗。
2. 開啟顯示的本機網址，通常為 `http://127.0.0.1:8501`。服務僅監聽本機。
3. 選擇 MP3／WAV／M4A，最長 5 分鐘、100 MB。
4. CPU 選 **small**；已完成 GPU 安裝的 RTX 3060 可先選 **turbo**。
5. 首次使用不要勾「僅使用已下載模型」，按「開始辨識」才會下載模型。
6. 模型快取在專案的 `models` 資料夾。turbo 約需 1.6 GB 下載；首次下載可能花數分鐘或更久，與實際轉錄時間不同。
7. 完成後可編輯、拆併句、刪句、補時間及匯出 SRT。表格保留原文；輸出標點的效果看預覽與 SRT。

模型準備完成後可勾「僅使用已下載模型」離線使用；尚未下載的另一個模型仍需要網路。設定 `AUTO_SUB_MODEL_DIR` 可改模型快取位置。

關閉前先下載專案 JSON；工作階段不自動存檔。停止服務可在啟動視窗按 **Ctrl+C**。

## 5. 常見問題

| 狀況 | 處理方式 |
| --- | --- |
| 找不到 Python／py | 安裝官方 64-bit Python 3.12，重開 PowerShell；或使用 `-PythonExecutable` 指定完整路徑。 |
| Python 版本或 32-bit 不相容 | 使用 64-bit Python 3.12，在新的解壓縮資料夾安裝。不要把其他電腦的 `.venv` 複製過來。 |
| DLL load failed／缺少 VCRUNTIME | 安裝 Microsoft 官方 [Visual C++ Redistributable x64](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)，再重試。 |
| 找得到 GPU，辨識時卻報 CUDA/cuDNN DLL 錯誤 | 執行 `install.ps1 -Gpu`、更新 NVIDIA 驅動並重新啟動工具；可先切 CPU 使用。`nvidia-smi` 版本不代表所有執行函式庫都已安裝。 |
| pip 或模型下載失敗 | 檢查網路、代理伺服器與剩餘磁碟空間，保留錯誤訊息後重試。不要關閉憑證驗證。 |
| 記憶體／VRAM 不足 | 換 small，關閉其他高用量程式後重啟；不強制同時載入多個模型。 |
| 網址無法開啟 | 確認啟動視窗仍在執行，檢查其錯誤訊息與實際網址。 |
| 8501 已占用 | 先關閉先前啟動的工具，或執行下方的替代連接埠命令。 |
| 離線時模型找不到 | 取消離線選項，先下載該模型；確認 `models` 資料夾未被搬走。 |

指定另一個本機連接埠：

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8502 --browser.gatherUsageStats false
```

## 開發與測試（一般使用者可跳過）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Dev
.\.venv\Scripts\python.exe -m pytest -q
```

需 GPU 與測試時合併成 `-Gpu -Dev`。安裝腳本以 `requirements-tested.txt` 作為版本約束：**只安裝所選功能需要的套件**。不要直接 `pip install -r requirements-tested.txt`，該檔包含完整開發機的 GPU 與測試工具清單。

瀏覽器操作測試另外需要 Edge、Playwright 及本機產生的測試音檔，詳見 README；不包含使用者錄音或開發機環境。
