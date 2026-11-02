# =====================================================================
#  Install Apex 24/7 Auto-Start Scheduled Task in Windows
# =====================================================================
$taskName = "ApexTrader247"
$workingDir = Split-Path -Parent $PSScriptRoot
$batPath = Join-Path $workingDir "RUN_APEX_247.bat"

Write-Host "Configuring Windows Scheduled Task: $taskName..." -ForegroundColor Cyan
Write-Host "Target Script: $batPath" -ForegroundColor Gray

# Action
$action = New-ScheduledTaskAction -Execute $batPath -WorkingDirectory $workingDir

# Trigger: At logon of any user and at system startup
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn

# Settings: Restart on failure, do not stop on battery, keep alive indefinitely
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -Priority 4

# Register or update task
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $triggerLogon -Settings $settings -Force | Out-Null
    Write-Host "✅ Scheduled Task '$taskName' registered successfully!" -ForegroundColor Green
    Write-Host "The trading system will now automatically launch upon Windows login and self-heal 24/7." -ForegroundColor Green
} catch {
    Write-Host "⚠️ Could not register scheduled task directly: $_" -ForegroundColor Yellow
    Write-Host "You can also run RUN_APEX_247.bat directly in a minimized window." -ForegroundColor Gray
}
