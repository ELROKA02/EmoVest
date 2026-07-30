$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

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
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller terminó con código $LASTEXITCODE."
    }

    $BuiltSidecar = Join-Path $BackendRoot "dist\emovest-backend.exe"
    if (-not (Test-Path -LiteralPath $BuiltSidecar -PathType Leaf)) {
        throw "PyInstaller no generó el backend esperado: $BuiltSidecar"
    }
    $BuiltInfo = Get-Item -LiteralPath $BuiltSidecar
    $Stream = [IO.File]::OpenRead($BuiltSidecar)
    try {
        $FirstByte = $Stream.ReadByte()
        $SecondByte = $Stream.ReadByte()
    }
    finally {
        $Stream.Dispose()
    }
    if (
        $BuiltInfo.Length -lt 1MB -or
        $FirstByte -ne [byte][char]"M" -or
        $SecondByte -ne [byte][char]"Z"
    ) {
        throw "El backend generado no es un ejecutable PE real; se rechaza el empaquetado."
    }

    Copy-Item -LiteralPath $BuiltSidecar -Destination $SidecarTarget -Force
}
finally {
    Pop-Location
}

Write-Host "Sidecar preparado en $SidecarTarget"
