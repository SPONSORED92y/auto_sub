$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Virtual environment missing. Follow README.md to install dependencies first.'
}
& $pythonPath -m streamlit run app.py --server.address 127.0.0.1 --server.maxUploadSize 100 --browser.gatherUsageStats false
