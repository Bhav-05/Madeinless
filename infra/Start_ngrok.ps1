# ═══════════════════════════════════════════════════════
#  TM1 — ngrok Tunnel Launcher (Windows PowerShell)
#  Run with: .\Start_ngrok.ps1
# ═══════════════════════════════════════════════════════

Write-Host ""
Write-Host "╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         TM1 — ngrok Tunnel Launcher          ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Check ngrok is available ────────────────────────
if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    Write-Host "❌  ngrok not found." -ForegroundColor Red
    Write-Host "    Download from: https://ngrok.com/download"
    Write-Host "    Then run: ngrok config add-authtoken <YOUR_TOKEN>"
    exit 1
}

# ── Check stack is running ───────────────────────────
$lokiRunning = docker ps --format "{{.Names}}" | Select-String "loki"
if (-not $lokiRunning) {
    Write-Host "⚠️  Stack not running. Starting now..." -ForegroundColor Yellow
    docker compose up -d
    Write-Host "⏳  Waiting 15s for services to initialize..."
    Start-Sleep -Seconds 15
}

Write-Host "✅  Stack is running." -ForegroundColor Green
Write-Host ""

# ── Write temp ngrok config ──────────────────────────
$ngrokConfig = @"
version: "2"
tunnels:
  loki:
    addr: 3100
    proto: http
  prometheus:
    addr: 9090
    proto: http
  frontend:
    addr: 8080
    proto: http
  locust:
    addr: 8089
    proto: http
"@

$configPath = "$env:TEMP\ngrok_aiops.yml"
$ngrokConfig | Out-File -FilePath $configPath -Encoding utf8
Write-Host "📄  ngrok config written to: $configPath"

# ── Start ngrok in background ────────────────────────
Write-Host "🚀  Starting ngrok tunnels (opening new window)..." -ForegroundColor Cyan
Start-Process -FilePath "ngrok" -ArgumentList "start --all --config `"$configPath`"" -WindowStyle Normal

Write-Host "⏳  Waiting 8s for tunnels to establish..."
Start-Sleep -Seconds 8

# ── Fetch tunnel URLs from ngrok API ────────────────
try {
    $tunnels = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels"
} catch {
    Write-Host "❌  Could not reach ngrok API at localhost:4040" -ForegroundColor Red
    Write-Host "    Make sure ngrok started correctly in the other window."
    exit 1
}

function Get-TunnelUrl($name) {
    $t = $tunnels.tunnels | Where-Object { $_.name -eq $name }
    if ($t) { return $t.public_url } else { return "NOT FOUND" }
}

$lokiUrl   = Get-TunnelUrl "loki"
$promUrl   = Get-TunnelUrl "prometheus"
$frontUrl  = Get-TunnelUrl "frontend"
$locustUrl = Get-TunnelUrl "locust"

# ── Print handoff card ───────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║           HANDOFF URLS  →  Send these to TM2 & TM3          ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║"
Write-Host "║  📋 LOKI (logs)"
Write-Host "║     $lokiUrl/loki/api/v1/query_range"
Write-Host "║"
Write-Host "║  📊 PROMETHEUS (metrics)"
Write-Host "║     $promUrl/api/v1/query"
Write-Host "║"
Write-Host "║  🛍️  FRONTEND (boutique app)"
Write-Host "║     $frontUrl"
Write-Host "║"
Write-Host "║  🦗 LOCUST (load generator UI)"
Write-Host "║     $locustUrl"
Write-Host "║"
Write-Host "╠══════════════════════════════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  💡 Once TM2 gives you THEIR ngrok URL, run:"
Write-Host "║     .\Set_ingest_url.ps1 https://<TM2-URL>.ngrok-free.app/ingest"
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# ── Save URLs to file for reference ─────────────────
$output = @"
LOKI_URL=$lokiUrl
PROMETHEUS_URL=$promUrl
FRONTEND_URL=$frontUrl
LOCUST_URL=$locustUrl
LOKI_QUERY=$lokiUrl/loki/api/v1/query_range
PROMETHEUS_QUERY=$promUrl/api/v1/query
"@
$output | Out-File -FilePath ".\ngrok_urls.txt" -Encoding utf8
Write-Host "💾  URLs saved to ngrok_urls.txt — share this with TM2!" -ForegroundColor Yellow
Write-Host ""

# ── Chaos scripts reminder ───────────────────────────
Write-Host "🔥  CHAOS COMMANDS (run in a new PowerShell to break the system):" -ForegroundColor Red
Write-Host ""
Write-Host "  Memory OOM on cartservice:"
Write-Host '    docker update --memory=50m --memory-swap=50m cartservice' -ForegroundColor White
Write-Host ""
Write-Host "  Hard kill (instant crash):"
Write-Host '    docker kill cartservice' -ForegroundColor White
Write-Host ""
Write-Host "  Restore cartservice:"
Write-Host '    docker update --memory=128m --memory-swap=256m cartservice; docker restart cartservice' -ForegroundColor White
Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")