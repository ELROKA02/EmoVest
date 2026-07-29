$ErrorActionPreference = "Stop"

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendRoot = Join-Path $RepositoryRoot "backend"
$BinaryDirectory = Join-Path $RepositoryRoot "frontend\src-tauri\binaries"
$SidecarTarget = Join-Path $BinaryDirectory "emovest-backend-x86_64-pc-windows-msvc.exe"
$VirtualenvPython = Join-Path $BackendRoot "venv\Scripts\python.exe"
$PythonCommand = if (Test-Path $VirtualenvPython) { $VirtualenvPython } else { "python" }

New-Item -ItemType Directory -Force -Path $BinaryDirectory | Out-Null

Push-Location $BackendRoot
try {
    & $PythonCommand -m PyInstaller --clean --noconfirm "emovest-backend.spec"
    Copy-Item -Force (Join-Path $BackendRoot "dist\emovest-backend.exe") $SidecarTarget
}
finally {
    Pop-Location
}

Write-Host "Sidecar preparado en $SidecarTarget"
