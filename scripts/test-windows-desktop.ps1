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

function Test-ProcessExists {
  param([Parameter(Mandatory = $true)][int]$ProcessId)

  try {
    $Process = [Diagnostics.Process]::GetProcessById($ProcessId)
    try {
      return -not $Process.HasExited
    }
    finally {
      $Process.Dispose()
    }
  }
  catch [ArgumentException] {
    return $false
  }
}

function Get-InstalledEmoVestProcesses {
  return @(
    Get-CimInstance -ClassName Win32_Process |
      Where-Object {
        $_.Name -match `
          "^(?:EmoVest|emovest-desktop|emovest-backend(?:-.+)?)\.exe$" -and
        -not [string]::IsNullOrWhiteSpace([string]$_.ExecutablePath) -and
        (Test-PathWithin -Candidate $_.ExecutablePath -Parent $InstallDir)
      }
  )
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

function Test-ProcessDescendsFrom {
  param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [Parameter(Mandatory = $true)][int]$AncestorProcessId
  )

  $Visited = [Collections.Generic.HashSet[int]]::new()
  $CurrentProcessId = $ProcessId
  while ($CurrentProcessId -gt 0 -and $Visited.Add($CurrentProcessId)) {
    if ($CurrentProcessId -eq $AncestorProcessId) {
      return $true
    }
    $Current = Get-CimInstance `
      -ClassName Win32_Process `
      -Filter "ProcessId = $CurrentProcessId"
    if (-not $Current) {
      return $false
    }
    $CurrentProcessId = [int]$Current.ParentProcessId
  }
  return $false
}

function Get-SidecarListener {
  param(
    [Parameter(Mandatory = $true)]
    [AllowEmptyCollection()]
    [object[]]$Processes
  )

  $Listeners = @(Get-NetTCPConnection -State Listen)
  foreach ($Process in $Processes) {
    $Listener = $Listeners |
      Where-Object {
        $_.OwningProcess -eq [int]$Process.ProcessId -and
        $_.LocalAddress -in @("127.0.0.1", "::1")
      } |
      Select-Object -First 1
    if ($Listener) {
      return $Listener
    }
  }
  return $null
}

function Test-PortReleased {
  param(
    [Parameter(Mandatory = $true)][int]$Port,
    [Parameter(Mandatory = $true)][int]$OwningProcessId
  )

  return $null -eq (
    Get-NetTCPConnection -State Listen |
      Where-Object {
        $_.LocalPort -eq $Port -and
        $_.OwningProcess -eq $OwningProcessId
      } |
      Select-Object -First 1
  )
}

function Write-DesktopProcessDiagnostics {
  param([Parameter(Mandatory = $true)][string]$Context)

  Write-Host "=== Diagnóstico de procesos: $Context ==="
  Write-Host "TestRoot=$TestRoot"
  Write-Host "InstallDir=$InstallDir"
  Write-Host "MainExecutable=$MainExecutable"
  Write-Host "SidecarExecutable=$SidecarExecutablePath"
  if ($MainProcess) {
    try {
      $MainProcess.Refresh()
      $MainState = if ($MainProcess.HasExited) {
        "salido; exitCode=$($MainProcess.ExitCode)"
      }
      else {
        "activo"
      }
      Write-Host "MainProcessId=$($MainProcess.Id); state=$MainState"
    }
    catch {
      Write-Warning "No se pudo consultar el proceso principal: $($_.Exception.Message)"
    }
  }

  try {
    $CapturedIds = @($MainProcessId, $SidecarProcessId) |
      Where-Object { $null -ne $_ }
    $Processes = @(
      Get-CimInstance -ClassName Win32_Process |
        Where-Object {
          $CapturedIds -contains [int]$_.ProcessId -or
          (
            -not [string]::IsNullOrWhiteSpace([string]$_.ExecutablePath) -and
            (Test-PathWithin -Candidate $_.ExecutablePath -Parent $InstallDir)
          )
        }
    )
  }
  catch {
    Write-Warning "No se pudo obtener el inventario CIM: $($_.Exception.Message)"
    return
  }
  if ($Processes.Count -eq 0) {
    Write-Host "No hay procesos EmoVest activos."
  }
  foreach ($Process in $Processes) {
    $Record = [ordered]@{
      ProcessId = [int]$Process.ProcessId
      ParentProcessId = [int]$Process.ParentProcessId
      Name = [string]$Process.Name
      ExecutablePath = [string]$Process.ExecutablePath
      CommandLine = [string]$Process.CommandLine
      CreationDate = [string]$Process.CreationDate
      State = "activo"
    }
    Write-Host ($Record | ConvertTo-Json -Compress)
  }

  try {
    $Listeners = @(Get-NetTCPConnection -State Listen)
    foreach ($Process in $Processes) {
      foreach (
        $Listener in @(
          $Listeners |
            Where-Object { $_.OwningProcess -eq [int]$Process.ProcessId }
        )
      ) {
        Write-Host (
          "Listener PID=$($Process.ProcessId) " +
          "$($Listener.LocalAddress):$($Listener.LocalPort)"
        )
      }
    }
  }
  catch {
    Write-Warning "No se pudieron enumerar listeners: $($_.Exception.Message)"
  }
}

function Write-FileLockDiagnostics {
  param([Parameter(Mandatory = $true)][string]$Path)

  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    Write-Host "El archivo ya no existe para consultar handles: $Path"
    return
  }
  try {
    $Lockers = @([EmoVestRestartManager]::GetLockingProcesses($Path))
    if ($Lockers.Count -eq 0) {
      Write-Host "Restart Manager no detectó procesos con handles sobre: $Path"
    }
    foreach ($Locker in $Lockers) {
      Write-Host "Handle detectado por Restart Manager: $Locker"
    }
  }
  catch {
    Write-Warning "Restart Manager no pudo inspeccionar el archivo: $($_.Exception.Message)"
  }
}

function Stop-InstalledEmoVestProcesses {
  $Deadline = [DateTime]::UtcNow.AddSeconds(20)
  while ([DateTime]::UtcNow -lt $Deadline) {
    $Processes = @(Get-InstalledEmoVestProcesses)
    if ($Processes.Count -eq 0) {
      return
    }

    foreach ($Process in ($Processes | Sort-Object ParentProcessId -Descending)) {
      $Current = Get-CimInstance `
        -ClassName Win32_Process `
        -Filter "ProcessId = $($Process.ProcessId)"
      if (-not $Current) {
        continue
      }
      if (
        [string]$Current.CreationDate -ne [string]$Process.CreationDate -or
        [string]::IsNullOrWhiteSpace([string]$Current.ExecutablePath) -or
        -not (Test-PathWithin `
          -Candidate $Current.ExecutablePath `
          -Parent $InstallDir)
      ) {
        throw "El PID $($Process.ProcessId) cambió de identidad durante la limpieza."
      }

      try {
        Stop-Process -Id ([int]$Process.ProcessId) -Force
      }
      catch {
        if (Test-ProcessExists -ProcessId ([int]$Process.ProcessId)) {
          throw
        }
        Write-Host "El PID $($Process.ProcessId) terminó antes de Stop-Process."
      }
    }
    Start-Sleep -Milliseconds 200
  }

  $Remaining = @(Get-InstalledEmoVestProcesses)
  if ($Remaining.Count -gt 0) {
    $Ids = ($Remaining | ForEach-Object { $_.ProcessId }) -join ", "
    throw "No terminaron los procesos de la instalación temporal: $Ids"
  }
}

function Remove-TestRootWithRetry {
  Assert-CiTemporaryPath -Path $TestRoot
  $Delays = @(100, 200, 400, 800, 1000, 1500, 2000, 2500)
  for ($Attempt = 0; $Attempt -lt $Delays.Count; $Attempt += 1) {
    try {
      Remove-Item -LiteralPath $TestRoot -Recurse -Force
      if (-not (Test-Path -LiteralPath $TestRoot)) {
        return
      }
    }
    catch {
      Write-Warning (
        "Intento $($Attempt + 1)/$($Delays.Count) de limpieza falló: " +
        $_.Exception.Message
      )
      Write-DesktopProcessDiagnostics -Context "fallo al borrar TestRoot"
      if ($SidecarExecutablePath) {
        Write-FileLockDiagnostics -Path $SidecarExecutablePath
      }
      if ($Attempt -eq $Delays.Count - 1) {
        throw
      }
    }
    Start-Sleep -Milliseconds $Delays[$Attempt]
  }
  throw "El directorio temporal sigue existiendo después de todos los intentos."
}

Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public static class EmoVestRestartManager
{
    private const int ErrorMoreData = 234;
    private const int SessionKeyLength = 32;

    [StructLayout(LayoutKind.Sequential)]
    private struct UniqueProcess
    {
        public int ProcessId;
        public System.Runtime.InteropServices.ComTypes.FILETIME ProcessStartTime;
    }

    private enum ApplicationType
    {
        Unknown = 0,
        MainWindow = 1,
        OtherWindow = 2,
        Service = 3,
        Explorer = 4,
        Console = 5,
        Critical = 1000
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct ProcessInfo
    {
        public UniqueProcess Process;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 256)]
        public string ApplicationName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)]
        public string ServiceShortName;
        public ApplicationType ApplicationType;
        public uint ApplicationStatus;
        public uint TerminalServicesSessionId;
        [MarshalAs(UnmanagedType.Bool)]
        public bool Restartable;
    }

    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    private static extern int RmStartSession(
        out uint sessionHandle,
        int sessionFlags,
        StringBuilder sessionKey
    );

    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    private static extern int RmRegisterResources(
        uint sessionHandle,
        uint fileCount,
        string[] fileNames,
        uint applicationCount,
        IntPtr applications,
        uint serviceCount,
        string[] serviceNames
    );

    [DllImport("rstrtmgr.dll")]
    private static extern int RmGetList(
        uint sessionHandle,
        out uint processInfoNeeded,
        ref uint processInfoCount,
        [In, Out] ProcessInfo[] processInfo,
        ref uint rebootReasons
    );

    [DllImport("rstrtmgr.dll")]
    private static extern int RmEndSession(uint sessionHandle);

    public static string[] GetLockingProcesses(string path)
    {
        uint sessionHandle;
        var sessionKey = new StringBuilder(SessionKeyLength + 1);
        int result = RmStartSession(out sessionHandle, 0, sessionKey);
        if (result != 0)
            throw new InvalidOperationException("RmStartSession devolvió " + result);

        try
        {
            result = RmRegisterResources(
                sessionHandle,
                1,
                new[] { path },
                0,
                IntPtr.Zero,
                0,
                null
            );
            if (result != 0)
                throw new InvalidOperationException("RmRegisterResources devolvió " + result);

            uint needed = 0;
            uint count = 0;
            uint rebootReasons = 0;
            result = RmGetList(
                sessionHandle,
                out needed,
                ref count,
                null,
                ref rebootReasons
            );
            if (result == 0)
                return Array.Empty<string>();
            if (result != ErrorMoreData)
                throw new InvalidOperationException("RmGetList devolvió " + result);

            var processInfo = new ProcessInfo[needed];
            count = needed;
            result = RmGetList(
                sessionHandle,
                out needed,
                ref count,
                processInfo,
                ref rebootReasons
            );
            if (result != 0)
                throw new InvalidOperationException("RmGetList devolvió " + result);

            var lockingProcesses = new List<string>();
            for (int index = 0; index < count; index++)
            {
                lockingProcesses.Add(
                    "PID=" + processInfo[index].Process.ProcessId +
                    "; app=" + processInfo[index].ApplicationName +
                    "; service=" + processInfo[index].ServiceShortName
                );
            }
            return lockingProcesses.ToArray();
        }
        finally
        {
            RmEndSession(sessionHandle);
        }
    }
}

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

$InstallerProcess = $null
$MainProcess = $null
$MainProcessStarted = $false
$MainExecutable = $null
$MainProcessId = $null
$SidecarProcessId = $null
$SidecarExecutablePath = Join-Path $InstallDir "emovest-backend.exe"
$SidecarPort = $null
$Validated = $false
$PrimaryFailure = $null
$CleanupFailure = $null

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
    if (-not $InstallerProcess.WaitForExit(10000)) {
      throw "El instalador tampoco terminó después de forzar su cierre."
    }
    throw "El instalador NSIS no terminó dentro del plazo."
  }
  if ($InstallerProcess.ExitCode -ne 0) {
    throw "El instalador NSIS terminó con código $($InstallerProcess.ExitCode)."
  }
  $InstallerProcess.Dispose()
  $InstallerProcess = $null

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

  $StartupDeadline = [DateTime]::UtcNow.AddSeconds(25)
  $VisibleWindow = $false
  $SidecarListener = $null
  while ([DateTime]::UtcNow -lt $StartupDeadline) {
    $MainProcess.Refresh()
    if ($MainProcess.HasExited) {
      if ($MainProcess.ExitCode -eq 101) {
        throw "EmoVest terminó con código 101 antes de mostrar su ventana."
      }
      throw "EmoVest terminó prematuramente con código $($MainProcess.ExitCode)."
    }

    if (-not $SidecarProcessId) {
      $Sidecar = Get-ChildSidecar -ParentProcessId $MainProcessId
      if ($Sidecar) {
        $SidecarProcessId = [int]$Sidecar.ProcessId
        $SidecarExecutablePath = [string]$Sidecar.ExecutablePath
      }
    }

    $Backends = @(
      Get-InstalledEmoVestProcesses |
        Where-Object {
          $_.Name -match "^emovest-backend(?:-.+)?\.exe$" -and
          $SidecarProcessId -and
          (Test-ProcessDescendsFrom `
            -ProcessId ([int]$_.ProcessId) `
            -AncestorProcessId $SidecarProcessId)
        }
    )
    $SidecarListener = Get-SidecarListener -Processes $Backends
    $WindowHandle = $MainProcess.MainWindowHandle
    $VisibleWindow = (
      $WindowHandle -ne [IntPtr]::Zero -and
      [EmoVestNativeWindow]::IsWindowVisible($WindowHandle)
    )
    if (
      $VisibleWindow -and
      $SidecarProcessId -and
      (Test-ProcessExists -ProcessId $SidecarProcessId) -and
      $SidecarListener
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
  if (-not $SidecarListener) {
    throw "Ningún proceso del sidecar abrió un listener limitado a loopback."
  }
  $SidecarPort = [int]$SidecarListener.LocalPort
  $SidecarListenerProcessId = [int]$SidecarListener.OwningProcess
  if (
    [string]::IsNullOrWhiteSpace($SidecarExecutablePath) -or
    -not (Test-PathWithin -Candidate $SidecarExecutablePath -Parent $InstallDir)
  ) {
    throw "El sidecar activo no pertenece a la instalación temporal validada."
  }

  Write-DesktopProcessDiagnostics -Context "aplicación lista antes del cierre"
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
  do {
    $RemainingBackends = @(
      Get-InstalledEmoVestProcesses |
        Where-Object {
          $_.Name -match "^emovest-backend(?:-.+)?\.exe$"
        }
    )
    if ($RemainingBackends.Count -eq 0) {
      break
    }
    Start-Sleep -Milliseconds 200
  } while ([DateTime]::UtcNow -lt $SidecarDeadline)

  if ($RemainingBackends.Count -gt 0) {
    Write-DesktopProcessDiagnostics -Context "sidecar huérfano tras cierre normal"
    throw "Quedaron procesos del sidecar pertenecientes a la instalación temporal."
  }
  if (
    -not (Test-PortReleased `
      -Port $SidecarPort `
      -OwningProcessId $SidecarListenerProcessId)
  ) {
    throw "El puerto $SidecarPort del backend sigue ocupado tras cerrar EmoVest."
  }

  $Validated = $true
}
catch {
  $PrimaryFailure = $_
}
finally {
  try {
    if ($InstallerProcess) {
      if (-not $InstallerProcess.HasExited) {
        try {
          $InstallerProcess.Kill($true)
        }
        catch {
          $InstallerProcess.Refresh()
          if (-not $InstallerProcess.HasExited) {
            throw
          }
        }
        if (-not $InstallerProcess.WaitForExit(10000)) {
          throw "El instalador no terminó durante la limpieza."
        }
      }
      $InstallerProcess.Dispose()
      $InstallerProcess = $null
    }

    if ($MainProcess) {
      if ($MainProcessStarted -and -not $MainProcess.HasExited) {
        try {
          $MainProcess.Kill($true)
        }
        catch {
          $MainProcess.Refresh()
          if (-not $MainProcess.HasExited) {
            throw
          }
        }
        if (-not $MainProcess.WaitForExit(10000)) {
          throw "EmoVest no terminó durante la limpieza forzada."
        }
      }
      $MainProcess.Dispose()
      $MainProcess = $null
    }

    Stop-InstalledEmoVestProcesses
    Write-DesktopProcessDiagnostics -Context "antes de borrar TestRoot"
    if (Test-Path -LiteralPath $TestRoot) {
      Remove-TestRootWithRetry
    }
  }
  catch {
    $CleanupFailure = $_
  }
}

if ($PrimaryFailure) {
  if ($CleanupFailure) {
    throw (
      "La prueba falló: $($PrimaryFailure.Exception.Message) " +
      "La limpieza también falló: $($CleanupFailure.Exception.Message)"
    )
  }
  throw $PrimaryFailure
}
if ($CleanupFailure) {
  throw $CleanupFailure
}
if (-not $Validated) {
  throw "La validación de escritorio no terminó correctamente."
}

Write-Host (
  "Aplicación Windows validada: instalación, ventana visible, sidecar hijo, " +
  "cierre sin huérfanos, puerto liberado y limpieza completa."
)
