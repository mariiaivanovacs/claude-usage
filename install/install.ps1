# Install the Claude usage collector on Windows.
#
#   powershell -ExecutionPolicy Bypass -File install\install.ps1 [-Device NAME]
#   powershell -ExecutionPolicy Bypass -File install\install.ps1 -Uninstall
#
# Runs the collector every day at 08:00 Malaysia time (converted to this PC's
# clock), catches up if the PC was off or asleep, and adds a Claude Code
# SessionEnd hook.
param(
  [string]$Device = "",
  [switch]$Uninstall
)
$ErrorActionPreference = "Stop"

$RepoDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Base = if ($env:CLAUDE_USAGE_HOME) { $env:CLAUDE_USAGE_HOME } else { Join-Path $HOME ".claude-usage" }
$Collect = Join-Path $RepoDir "collector\collect.py"
$TaskName = "Claude usage collector"

function Find-Python {
  foreach ($c in @("python", "python3", "py")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) {
      $pyArgs = if ($c -eq "py") { @("-3", "-c", "import sys;print(sys.executable)") } else { @("-c", "import sys;print(sys.executable)") }
      $exe = & $cmd.Source @pyArgs 2>$null
      if ($LASTEXITCODE -eq 0 -and $exe -and (Test-Path $exe)) { return $exe.Trim() }
    }
  }
  throw "Python 3 is required. Install it with: winget install Python.Python.3.12"
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git is required. Install it with: winget install Git.Git" }

$Py = Find-Python
$PyW = Join-Path (Split-Path $Py) "pythonw.exe"
if (-not (Test-Path $PyW)) { $PyW = $Py }

if ($Uninstall) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  & $Py $Collect settings uninstall
  Write-Host "Uninstalled. Data already pushed stays in the repo; local state is in $Base."
  exit 0
}

# ---- device name ----------------------------------------------------------
New-Item -ItemType Directory -Force -Path $Base | Out-Null
$ConfigPath = Join-Path $Base "config.json"
$Config = @{}
if (Test-Path $ConfigPath) {
  (Get-Content $ConfigPath -Raw | ConvertFrom-Json).PSObject.Properties | ForEach-Object { $Config[$_.Name] = $_.Value }
}
if (-not $Device) { $Device = $Config["device"] }
if (-not $Device) {
  $guess = $env:COMPUTERNAME.ToLower()
  $answer = Read-Host "Device name [$guess]"
  $Device = if ($answer) { $answer } else { $guess }
}
$Device = ($Device.ToLower() -replace "[^a-z0-9-]", "-" -replace "-+", "-").Trim("-")
if (-not $Device) { throw "device name is empty" }
$Config["device"] = $Device
$Config | ConvertTo-Json | Set-Content -Encoding UTF8 $ConfigPath

# ---- repo: only this device's folder is checked out -------------------------
git -C $RepoDir sparse-checkout set --no-cone "/*" "!/devices/*" "/devices/$Device/" 2>$null | Out-Null

# ---- when to run: 08:00 Malaysia time (UTC+8, no DST) on this PC's clock -----
$myt = [DateTimeOffset]::new((Get-Date).Date.AddHours(8), [TimeSpan]::FromHours(8))
$local = $myt.ToLocalTime().DateTime
Write-Host ("Daily run: 08:00 Malaysia time = {0:HH:mm} on this PC" -f $local)

$action = New-ScheduledTaskAction -Execute $PyW -Argument "`"$Collect`"" -WorkingDirectory $RepoDir
$triggers = @(
  (New-ScheduledTaskTrigger -Daily -At $local),
  (New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME")
)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers -Settings $settings `
  -Description "Syncs Claude Code usage to the claude-usage repo" -Force | Out-Null
Write-Host "Scheduled task '$TaskName' registered. Missed runs happen when the PC is next available."

# ---- Claude Code settings: SessionEnd hook + keep transcripts a year --------
& $Py $Collect settings install

# ---- first run: import all history now -------------------------------------
Write-Host "Importing existing history (can take a minute the first time)..."
& $Py $Collect
Write-Host "Done. Device '$Device' is set up. Log: $(Join-Path $Base 'collect.log')"
