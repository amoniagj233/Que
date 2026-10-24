# Run this yourself to apply the reviewed code to the existing REAL-account bot.
# No positions are closed by this script. The bot resumes its usual trading loop.
$ErrorActionPreference = 'Stop'
$botDirectory = 'C:\Users\amoni\.gemini\antigravity\scratch\mt5_trade_agent'
$botScript = Join-Path $botDirectory 'run_liquidity_bot.py'
$pythonExecutable = 'C:\Program Files\Python314\python.exe'
$terminalPath = 'C:\Program Files\Headway MT5 Terminal\terminal64.exe'
$reviewDirectory = $PSScriptRoot

$manifest = Get-Content -LiteralPath (Join-Path $reviewDirectory 'reviewed_sha256.json') -Raw | ConvertFrom-Json
$expectedBuild = (Get-Content -LiteralPath (Join-Path $reviewDirectory 'expected_execution_build.txt') -Raw).Trim()
foreach ($property in $manifest.PSObject.Properties) {
    $sourceFile = Join-Path $botDirectory $property.Name
    if ((Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $property.Value) {
        throw "Reviewed source changed: $($property.Name). Review and retest before activation."
    }
}

Push-Location $botDirectory
try {
    & $pythonExecutable -m unittest test_execution_safety test_agent -q
    if ($LASTEXITCODE -ne 0) { throw 'Offline regression tests failed. Existing bot was not stopped.' }
} finally { Pop-Location }

$probeCode = @'
import MetaTrader5 as mt5,json
if not mt5.initialize(path=r'C:\Program Files\Headway MT5 Terminal\terminal64.exe'):
    raise SystemExit('Expected terminal unavailable')
account=mt5.account_info();positions=mt5.positions_get()
if account is None or positions is None:
    raise SystemExit('Account or positions unavailable')
if account.trade_mode != 2 or account.server != 'Headway-Real':
    raise SystemExit('Expected Headway-Real account is not selected')
owned=[p for p in positions if p.magic==20260912]
if any(p.sl <= 0 or p.tp <= 0 for p in owned):
    raise SystemExit('An owned position lacks SL/TP. Protect it before restarting.')
if any(p.sl <= 0 for p in positions):
    raise SystemExit('Account positions lack stop losses. Set your chosen stops before activating new entries.')
print(json.dumps({'server':account.server,'balance':account.balance,'equity':account.equity,'owned_open_positions':len(owned)}))
'@
$probeOutput = $probeCode | & $pythonExecutable -
if ($LASTEXITCODE -ne 0) { throw 'Read-only account verification failed. Existing bot was not stopped.' }
Write-Host $probeOutput
Write-Host 'This restarts REAL-account XAUUSD M5 automation: 0.01 lots, 0.5% pre-trade stop-risk budget, up to four bot-owned positions.'
Write-Host 'Daily loss protection remains at its existing setting; it is disabled at 100% unless you explicitly configured another value.'
Write-Host 'Existing positions remain open. The restarted bot will manage its positions and may place eligible new orders.'
$activation = Read-Host 'Type ACTIVATE to perform the real-account restart yourself, or press Enter to cancel'
if ($activation -cne 'ACTIVATE') { Write-Host 'Cancelled. Existing process was not changed.'; exit }
foreach ($property in $manifest.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $botDirectory $property.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $property.Value) {
        throw 'Reviewed code changed while waiting. Existing process was not stopped.'
    }
}

$matching = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match [regex]::Escape($botScript)
})
if ($matching.Count -gt 1) { throw 'Multiple matching bots found. Resolve duplicate processes before activation.' }
if ($matching.Count -eq 1) {
    $verified = Get-CimInstance Win32_Process -Filter "ProcessId=$($matching[0].ProcessId)"
    if ($verified.CommandLine -ne $matching[0].CommandLine -or
        $verified.CommandLine -notmatch [regex]::Escape($terminalPath) -or
        $verified.CommandLine -notmatch '--mode\s+live' -or
        $verified.CommandLine -notmatch '--timeframe\s+M5(?:\s|$)' -or
        $verified.CommandLine -notmatch '--symbols\s+XAUUSD(?:\s|$)' -or
        $verified.CommandLine -notmatch '--flat-lot\s+0\.01(?:\s|$)') {
        throw 'Process identity or expected live terminal changed. Restart cancelled.'
    }
    Stop-Process -Id $verified.ProcessId
    Wait-Process -Id $verified.ProcessId -Timeout 10 -ErrorAction SilentlyContinue
}
$finalProbe = $probeCode | & $pythonExecutable -
if ($LASTEXITCODE -ne 0) { throw 'Final account/protection check failed. Old process is stopped; protect positions and review before relaunching.' }
$launchArguments = @('-u', ('"' + $botScript + '"'), '--path', ('"' + $terminalPath + '"'),
    '--flat-lot', '0.01', '--mode', 'live', '--symbols', 'XAUUSD', '--timeframe', 'M5',
    '--interval', '5', '--risk', '0.5', '--max-trades', '4')
$activationTime = [DateTimeOffset]::UtcNow
$launched = Start-Process -FilePath $pythonExecutable -ArgumentList $launchArguments -WorkingDirectory $botDirectory `
    -WindowStyle Hidden -RedirectStandardOutput (Join-Path $botDirectory 'reviewed_bot.stdout.log') `
    -RedirectStandardError (Join-Path $botDirectory 'reviewed_bot.stderr.log') -PassThru
for ($check = 0; $check -lt 15; $check++) {
    Start-Sleep -Seconds 1
    try {
        $telemetry = Get-Content -LiteralPath (Join-Path $botDirectory 'live_telemetry.json') -Raw | ConvertFrom-Json
        if ($telemetry.execution_version -eq 'protected-journal-v2' -and $telemetry.execution_build -eq $expectedBuild -and
            [DateTimeOffset]::Parse($telemetry.timestamp) -ge $activationTime) {
            Write-Host "Reviewed bot loaded. Process $($launched.Id), status $($telemetry.status)."
            Write-Host 'Inspect live_telemetry.json and entry_decisions.jsonl for fills and exact blockers.'
            exit
        }
    } catch { }
}
throw 'No fresh reviewed-version heartbeat yet. Inspect reviewed_bot.stderr.log; do not launch a second instance.'
