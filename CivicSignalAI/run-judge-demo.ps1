$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot

$env:CIVICSIGNAL_DATABASE_PATH = Join-Path $projectRoot "data\judge-demo.db"
$env:CIVICSIGNAL_UPLOAD_DIR = Join-Path $projectRoot "data\private-uploads\judge-demo"
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
} else {
    $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonLauncher) {
        & $pythonLauncher.Source -3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    } else {
        $python = Get-Command python -ErrorAction Stop
        & $python.Source -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    }
}

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
