param(
  [string]$TaskName = "SmileUpDailyMarketingScan",
  [string]$Time = "08:30"
)

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = (Get-Command python).Source
$script = Join-Path $root "scripts\run_daily_scan.py"
$action = New-ScheduledTaskAction -Execute $python -Argument "`"$script`"" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Daily SmileUp Meta Ad Library scan and strategy generation" -Force
Write-Host "Installed $TaskName at $Time"
