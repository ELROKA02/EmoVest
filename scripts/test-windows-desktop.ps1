$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($env:GITHUB_ACTIONS -ne "true" -or $env:CI -ne "true") {
  throw "Esta prueba instala y elimina una copia temporal; solo puede ejecutarse en GitHub Actions."
}
if ([string]::IsNullOrWhiteSpace($env:RUNNER_TEMP)) {
  throw "RUNNER_TEMP es obligatorio para aislar la instalación de prueba."
}

$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RunnerTemp = (Resolve-Path $env:RUNNER_TEMP).Path.TrimEnd("\")
$ProtectedDataPath = [IO.Path]::GetFullPath(
  "C:\Users\rmaad\AppData\Local\EmoVest"
).TrimEnd("\")
$TestRoot = Join-Path `
  $RunnerTemp `
  "EmoVest CI ñ con espacios\$([Guid]::NewGuid().ToString("N"))"
$InstallDir = Join-Path $TestRoot "aplicación instalada"
$ProfileRoot = Join-Path $TestRoot "perfil temporal"
$LocalAppData = Join-Path $ProfileRoot "AppData\Local"
$RoamingAppData = Join-Path $ProfileRoot "AppData\Roaming"

function Assert-CiTemporaryPath {
  param([Parameter(Mandatory = $true)][string]$Path)

  $FullPath = [IO.Path]::GetFullPath($Path).TrimEnd("\")
  $RunnerPrefix = "$RunnerTemp\"
  $ProtectedPrefix = "$ProtectedDataPath\"
  if (
    $FullPath.Equals($ProtectedDataPath, [StringComparison]::OrdinalIgnoreCase) -or
    $FullPath.StartsWith($ProtectedPrefix, [StringComparison]::OrdinalIgnoreCase)
  ) {
    throw "La prueba nunca puede modificar la ruta protegida: $ProtectedDataPath"
  }
  if (
    $FullPath.Equals($RunnerTemp, [StringComparison]::OrdinalIgnoreCase) -or
    -not $FullPath.StartsWith($RunnerPrefix, [StringComparison]::OrdinalIgnoreCase)
  ) {
    throw "La ruta de prueba debe ser descendiente de RUNNER_TEMP: $FullPath"
  }
}

function Test-ProcessExists {
  param([Parameter(Mandatory = $true)][int]$ProcessId)

  return $null -ne (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

function Get-ChildSidecar {
  param([Parameter(Mandatory = $true)][int]$ParentProcessId)

  return Get-CimInstance `
    -ClassName Win32_Process `
    -Filter "ParentProcessId = $ParentProcessId" |
    Where-Object {
      $_.Name -match "^emovest-backend(?:-.+)?\.exe$"
    } |
    Select-Object -First 1
}

function Test-SidecarListening {
  param([Parameter(Mandatory = $true)][int]$ProcessId)

  return $null -ne (
    Get-NetTCPConnection `
      -OwningProcess $ProcessId `
      -State Listen `
      -ErrorAction SilentlyContinue |
    Where-Object {
      $_.LocalAddress -in @("127.0.0.1", "::1")
    } |
    Select-Object -First 1
  )
}

function Test-PathWithin {
  param(
    [Parameter(Mandatory = $true)][string]$Candidate,
    [Parameter(Mandatory = $true)][string]$Parent
  )

  $CandidatePath = [IO.Path]::GetFullPath($Candidate).TrimEnd("\")
  $ParentPath = [IO.Path]::GetFullPath($Parent).TrimEnd("\")
  return $CandidatePath.StartsWith(
    "$ParentPath\",
    [StringComparison]::OrdinalIgnoreCase
  )
}

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class EmoVestNativeWindow
{
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool IsWindowVisible(IntPtr windowHandle);
}
"@

Assert-CiTemporaryPath -Path $TestRoot
$Installer = Get-ChildItem `
  (Join-Path $RepositoryRoot "frontend\src-tauri\target\release\bundle\nsis") `
  -Filter "*-setup.exe" |
  Select-Object -First 1
if (-not $Installer) {
  throw "No existe el instalador NSIS que debe validar la prueba."
}

$MainProcess = $null
$MainProcessStarted = $false
$SidecarProcessId = $null
$SidecarExecutablePath = $null
$Validated = $false

try {
  New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
  New-Item -ItemType Directory -Force -Path $LocalAppData | Out-Null
  New-Item -ItemType Directory -Force -Path $RoamingAppData | Out-Null

  $InstallerStartInfo = [Diagnostics.ProcessStartInfo]::new()
  $InstallerStartInfo.FileName = $Installer.FullName
  $InstallerStartInfo.Arguments = "/S /D=$InstallDir"
  $InstallerStartInfo.UseShellExecute = $false
  $InstallerStartInfo.CreateNoWindow = $true
  $InstallerProcess = [Diagnostics.Process]::Start($InstallerStartInfo)
  if (-not $InstallerProcess) {
    throw "Windows no pudo iniciar el instalador NSIS."
  }
  if (-not $InstallerProcess.WaitForExit(180000)) {
    $InstallerProcess.Kill($true)
    $InstallerProcess.WaitForExit()
    $InstallerProcess.Dispose()
    throw "El instalador NSIS no terminó dentro del plazo."
  }
  $InstallerExitCode = $InstallerProcess.ExitCode
  $InstallerProcess.Dispose()
  if ($InstallerExitCode -ne 0) {
    throw "El instalador NSIS terminó con código $InstallerExitCode."
  }

  $MainExecutable = @(
    (Join-Path $InstallDir "EmoVest.exe"),
    (Join-Path $InstallDir "emovest-desktop.exe")
  ) |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1
  if (-not $MainExecutable) {
    $MainExecutable = Get-ChildItem $InstallDir -Recurse -Filter "*.exe" |
      Where-Object {
        $_.Name -notmatch "^(?:uninstall|emovest-backend(?:-.+)?)\.exe$"
      } |
      Select-Object -ExpandProperty FullName -First 1
  }
  if (-not $MainExecutable) {
    throw "La instalación terminó, pero no contiene el ejecutable de EmoVest."
  }
  if (-not (Test-PathWithin -Candidate $MainExecutable -Parent $InstallDir)) {
    throw "El ejecutable instalado quedó fuera del directorio temporal."
  }

  $ApplicationStartInfo = [Diagnostics.ProcessStartInfo]::new()
  $ApplicationStartInfo.FileName = $MainExecutable
  $ApplicationStartInfo.WorkingDirectory = $InstallDir
  $ApplicationStartInfo.UseShellExecute = $false
  $ApplicationStartInfo.CreateNoWindow = $true
  $ApplicationStartInfo.Environment["USERPROFILE"] = $ProfileRoot
  $ApplicationStartInfo.Environment["LOCALAPPDATA"] = $LocalAppData
  $ApplicationStartInfo.Environment["APPDATA"] = $RoamingAppData
  $ApplicationStartInfo.Environment["EMOVEST_DATA_DIR"] = Join-Path $TestRoot "datos"
  $ApplicationStartInfo.Environment["EMOVEST_CONFIG_DIR"] = Join-Path $TestRoot "configuración"
  $ApplicationStartInfo.Environment["EMOVEST_LOG_DIR"] = Join-Path $TestRoot "registros"
  $ApplicationStartInfo.Environment["EMOVEST_BACKUP_DIR"] = Join-Path $TestRoot "copias"
  $ApplicationStartInfo.Environment["EMOVEST_DATABASE_PATH"] = Join-Path `
    $TestRoot `
    "datos\emovest.sqlite3"
  $ApplicationStartInfo.Environment["IMAGE_STORAGE_DIR"] = Join-Path `
    $TestRoot `
    "datos\imágenes"
  $ApplicationStartInfo.Environment["EMOVEST_MODEL_DIR"] = Join-Path `
    $TestRoot `
    "datos\modelos"
  $MainProcess = [Diagnostics.Process]::new()
  $MainProcess.StartInfo = $ApplicationStartInfo
  if (-not $MainProcess.Start()) {
    throw "Windows no pudo iniciar la aplicación instalada."
  }
  $MainProcessStarted = $true
  $MainProcessId = $MainProcess.Id

  # El watchdog Rust muestra una ventana de error a los 30 s. Validar antes de
  # ese límite evita confundir ese fallback con una aplicación lista.
  $StartupDeadline = [DateTime]::UtcNow.AddSeconds(25)
  $VisibleWindow = $false
  $SidecarListening = $false
  while ([DateTime]::UtcNow -lt $StartupDeadline) {
    $MainProcess.Refresh()
    if ($MainProcess.HasExited) {
      $EarlyExitCode = $MainProcess.ExitCode
      if ($EarlyExitCode -eq 101) {
        throw "EmoVest terminó con código 101 antes de mostrar su ventana."
      }
      throw "EmoVest terminó prematuramente con código $EarlyExitCode."
    }

    if (-not $SidecarProcessId) {
      $Sidecar = Get-ChildSidecar -ParentProcessId $MainProcessId
      if ($Sidecar) {
        $SidecarProcessId = [int]$Sidecar.ProcessId
        $SidecarExecutablePath = [string]$Sidecar.ExecutablePath
      }
    }

    $WindowHandle = $MainProcess.MainWindowHandle
    $VisibleWindow = (
      $WindowHandle -ne [IntPtr]::Zero -and
      [EmoVestNativeWindow]::IsWindowVisible($WindowHandle)
    )
    if ($SidecarProcessId) {
      $SidecarListening = Test-SidecarListening -ProcessId $SidecarProcessId
    }
    if (
      $VisibleWindow -and
      $SidecarProcessId -and
      (Test-ProcessExists -ProcessId $SidecarProcessId) -and
      $SidecarListening
    ) {
      break
    }
    Start-Sleep -Milliseconds 250
  }

  if (-not $VisibleWindow) {
    throw "EmoVest no mostró una ventana visible dentro del plazo."
  }
  if (-not $SidecarProcessId -or -not (Test-ProcessExists $SidecarProcessId)) {
    throw "EmoVest no mantuvo un sidecar hijo activo."
  }
  if (-not $SidecarListening) {
    throw "El sidecar hijo no abrió un listener limitado a loopback."
  }
  if (
    [string]::IsNullOrWhiteSpace($SidecarExecutablePath) -or
    -not (Test-PathWithin -Candidate $SidecarExecutablePath -Parent $InstallDir)
  ) {
    throw "El sidecar activo no pertenece a la instalación temporal validada."
  }

  if (-not $MainProcess.CloseMainWindow()) {
    throw "Windows no pudo solicitar el cierre normal de la ventana de EmoVest."
  }
  if (-not $MainProcess.WaitForExit(30000)) {
    throw "EmoVest no terminó dentro del plazo de cierre normal."
  }
  if ($MainProcess.ExitCode -eq 101) {
    throw "EmoVest terminó con código 101 durante el cierre."
  }
  if ($MainProcess.ExitCode -ne 0) {
    throw "EmoVest terminó con código $($MainProcess.ExitCode) durante el cierre."
  }

  $SidecarDeadline = [DateTime]::UtcNow.AddSeconds(20)
  while (
    (Test-ProcessExists -ProcessId $SidecarProcessId) -and
    [DateTime]::UtcNow -lt $SidecarDeadline
  ) {
    Start-Sleep -Milliseconds 200
  }
  if (Test-ProcessExists -ProcessId $SidecarProcessId) {
    throw "El sidecar quedó huérfano después de cerrar EmoVest."
  }

  $Orphans = Get-CimInstance -ClassName Win32_Process |
    Where-Object {
      $_.Name -match "^emovest-backend(?:-.+)?\.exe$" -and
      -not [string]::IsNullOrWhiteSpace([string]$_.ExecutablePath) -and
      (Test-PathWithin -Candidate $_.ExecutablePath -Parent $InstallDir)
    }
  if ($Orphans) {
    throw "Quedaron procesos de sidecar pertenecientes a la instalación temporal."
  }

  $Validated = $true
}
finally {
  if ($MainProcess) {
    if ($MainProcessStarted -and -not $MainProcess.HasExited) {
      $MainProcess.Kill($true)
      $MainProcess.WaitForExit()
    }
    $MainProcess.Dispose()
  }

  if ($SidecarProcessId -and (Test-ProcessExists -ProcessId $SidecarProcessId)) {
    $SidecarForCleanup = Get-CimInstance `
      -ClassName Win32_Process `
      -Filter "ProcessId = $SidecarProcessId"
    if (
      $SidecarForCleanup -and
      -not [string]::IsNullOrWhiteSpace([string]$SidecarForCleanup.ExecutablePath) -and
      (Test-PathWithin `
        -Candidate $SidecarForCleanup.ExecutablePath `
        -Parent $InstallDir)
    ) {
      Stop-Process -Id $SidecarProcessId -Force -ErrorAction SilentlyContinue
    }
  }

  if (Test-Path $TestRoot) {
    Assert-CiTemporaryPath -Path $TestRoot
    Remove-Item -LiteralPath $TestRoot -Recurse -Force
  }
}

if (-not $Validated) {
  throw "La validación de escritorio no terminó correctamente."
}

Write-Host `
  "Aplicación Windows validada: instalación, ventana visible, sidecar hijo y cierre sin huérfanos."
