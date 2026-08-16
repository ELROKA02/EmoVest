$ErrorActionPreference = "Stop"

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ExpectedSchemaRevision = (
  & python -c "import sys; sys.path.insert(0, r'$RepositoryRoot\\backend'); from migration_manager import get_head_revision; print(get_head_revision())"
).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($ExpectedSchemaRevision)) {
  throw "No se pudo resolver la revisión Alembic esperada para el sidecar."
}
$Sidecar = Join-Path `
  $RepositoryRoot `
  "frontend\src-tauri\binaries\emovest-backend-x86_64-pc-windows-msvc.exe"
if (-not (Test-Path $Sidecar)) {
  throw "No existe el sidecar Windows esperado: $Sidecar"
}

$ProfileRoot = Join-Path $env:RUNNER_TEMP "EmoVest sidecar ñ con espacios"
$Token = "ci-sidecar-smoke-token-" + ("0" * 48)
$StartInfo = [Diagnostics.ProcessStartInfo]::new()
$StartInfo.FileName = $Sidecar
$StartInfo.UseShellExecute = $false
$StartInfo.CreateNoWindow = $true
$StartInfo.RedirectStandardOutput = $true
$StartInfo.RedirectStandardError = $true
$StartInfo.Environment["APP_MODE"] = "desktop"
$StartInfo.Environment["EMOVEST_DESKTOP_TOKEN"] = $Token
$StartInfo.Environment["EMOVEST_DESKTOP_HOST"] = "127.0.0.1"
$StartInfo.Environment["EMOVEST_DESKTOP_PORT"] = "0"
$StartInfo.Environment["EMOVEST_DATA_DIR"] = Join-Path $ProfileRoot "datos"
$StartInfo.Environment["EMOVEST_CONFIG_DIR"] = Join-Path $ProfileRoot "configuración"
$StartInfo.Environment["EMOVEST_LOG_DIR"] = Join-Path $ProfileRoot "registros"
$StartInfo.Environment["EMOVEST_BACKUP_DIR"] = Join-Path $ProfileRoot "copias"
$StartInfo.Environment["EMOVEST_DATABASE_PATH"] = Join-Path $ProfileRoot "datos\emovest.sqlite3"
$StartInfo.Environment["IMAGE_STORAGE_DIR"] = Join-Path $ProfileRoot "datos\imágenes"
$StartInfo.Environment["EMOVEST_MODEL_DIR"] = Join-Path $ProfileRoot "datos\modelos"
$StartInfo.Environment["SECRET_KEY"] = ""

$Process = [Diagnostics.Process]::new()
$Process.StartInfo = $StartInfo
$ReadyLine = $null
$Started = $false

try {
  if (-not $Process.Start()) {
    throw "Windows no pudo iniciar el sidecar."
  }
  $Started = $true
  $Deadline = [DateTime]::UtcNow.AddSeconds(45)
  $ReadTask = $Process.StandardOutput.ReadLineAsync()
  while ([DateTime]::UtcNow -lt $Deadline -and -not $Process.HasExited) {
    if (-not $ReadTask.Wait(1000)) {
      continue
    }
    $Line = $ReadTask.Result
    if ($Line -and $Line.StartsWith("EMOVEST_READY ")) {
      $ReadyLine = $Line
      break
    }
    if ($Line -and $Line.StartsWith("EMOVEST_ERROR ")) {
      throw "El sidecar informó un error de arranque: $Line"
    }
    $ReadTask = $Process.StandardOutput.ReadLineAsync()
  }
  if (-not $ReadyLine) {
    $Failure = if ($Process.HasExited) {
      "Código=$($Process.ExitCode) Error=$($Process.StandardError.ReadToEnd())"
    }
    else {
      "El proceso seguía activo al vencer el timeout."
    }
    throw "El sidecar no quedó listo. $Failure"
  }

  $Ready = $ReadyLine.Substring("EMOVEST_READY ".Length) | ConvertFrom-Json
  $BaseUrl = "http://127.0.0.1:$($Ready.port)"

  try {
    Invoke-WebRequest -UseBasicParsing "$BaseUrl/health/ready" | Out-Null
    throw "La API aceptó una petición sin token."
  }
  catch {
    $StatusCode = $_.Exception.Response.StatusCode.value__
    if ($StatusCode -ne 401) {
      throw
    }
  }

  $Headers = @{ "X-Emovest-Desktop-Token" = $Token }
  $Health = Invoke-RestMethod -Headers $Headers "$BaseUrl/health/ready"
  if (-not $Health.ready -or $Health.schema_revision -ne $ExpectedSchemaRevision) {
    throw "El health check autenticado no confirmó el esquema esperado."
  }

  Invoke-RestMethod `
    -Method Post `
    -Headers $Headers `
    -ContentType "application/json" `
    -Body "{}" `
    "$BaseUrl/desktop/shutdown" | Out-Null
  if (-not $Process.WaitForExit(15000)) {
    throw "El sidecar no terminó dentro del plazo de apagado."
  }
  if ($Process.ExitCode -ne 0) {
    throw "El sidecar terminó con código $($Process.ExitCode)."
  }
}
finally {
  if ($Started -and -not $Process.HasExited) {
    $Process.Kill($true)
    $Process.WaitForExit()
  }
  $Process.Dispose()
}

Write-Host "Sidecar Windows validado: READY, token, SQLite y shutdown."
