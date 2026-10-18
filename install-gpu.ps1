$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create .venv and install the base project first. See README.md.'
}
& $pythonPath -m pip install -e '.[gpu]'
if ($LASTEXITCODE -ne 0) { throw 'GPU dependency installation failed.' }
