[CmdletBinding()]
param(
    [switch]$Gpu,
    [switch]$Dev,
    [string]$PythonExecutable
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$venvPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'

function Test-PythonRuntime {
    param([string]$Executable, [string[]]$PrefixArguments = @())
    try {
        $result = & $Executable @PrefixArguments -c 'import sys,struct; print(sys.version.split()[0]); sys.exit(0 if (3,11) <= sys.version_info[:2] < (3,14) and struct.calcsize(''P'')==8 else 1)' 2>$null
        return $LASTEXITCODE -eq 0
    } catch { return $false }
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    $runtime = $null
    $runtimeArguments = @()
    if ($PythonExecutable) {
        $runtime = (Get-Command $PythonExecutable -ErrorAction Stop).Source
        if (-not (Test-PythonRuntime $runtime)) { throw 'Use 64-bit Python 3.12 (recommended), 3.11, or 3.13.' }
    } else {
        $launcher = Get-Command py -ErrorAction SilentlyContinue
        if ($launcher) {
            foreach ($version in @('-3.12','-3.11','-3.13')) {
                if (Test-PythonRuntime -Executable $launcher.Source -PrefixArguments @($version)) {
                    $runtime = $launcher.Source
                    $runtimeArguments = @($version)
                    break
                }
            }
        }
        if (-not $runtime) {
            $candidate = Get-Command python -ErrorAction SilentlyContinue
            if ($candidate -and $candidate.Source -notmatch 'WindowsApps' -and (Test-PythonRuntime $candidate.Source)) {
                $runtime = $candidate.Source
            }
        }
    }
    if (-not $runtime) {
        throw 'Python not found. Install 64-bit Python 3.12 from python.org, then rerun setup.bat. See docs/INSTALL_WINDOWS.md.'
    }
    Write-Host 'Creating the project virtual environment...'
    & $runtime @runtimeArguments -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv.' }
}
if (-not (Test-PythonRuntime $venvPython)) { throw 'Existing .venv is incompatible. Use a fresh extracted source folder with 64-bit Python 3.12.' }

$extras = @()
if ($Gpu) { $extras += 'gpu' }
if ($Dev) { $extras += 'test' }
$target = '.'
if ($extras.Count) { $target = '.[' + ($extras -join ',') + ']' }
$installArguments = @('-m','pip','install','--disable-pip-version-check')
$constraints = Join-Path $PSScriptRoot 'requirements-tested.txt'
if (Test-Path -LiteralPath $constraints) { $installArguments += @('-c',$constraints) }
$installArguments += @('-e',$target)
Write-Host 'Installing dependencies. First installation requires Internet access.'
if ($Gpu) { Write-Host 'NVIDIA runtime packages require more than 1 GB of downloads.' }
& $venvPython @installArguments
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Keep the error message and see docs/INSTALL_WINDOWS.md.' }
& $venvPython -c 'import streamlit,faster_whisper,opencc; print(''Dependency import check passed.'')'
if ($LASTEXITCODE -ne 0) { throw 'Dependencies could not be imported. See the Microsoft Visual C++ runtime troubleshooting notes.' }
Write-Host ''
Write-Host 'Installation complete. Double-click start.bat to launch.'
if (-not $Gpu) { Write-Host 'CPU installation: choose CPU in the app, even if an NVIDIA GPU is detected.' }
Write-Host 'Models are downloaded only when transcription starts. See docs/INSTALL_WINDOWS.md.'
