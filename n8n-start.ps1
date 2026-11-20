# Starts n8n for the LifeCenter Telegram demo (CHG-001, specs/003-n8n-migration/plan.md).
#
# Reads ONLY N8N_WEBHOOK_URL from .env (the public Tailscale Funnel URL, e.g.
# https://<machine>.<tailnet>.ts.net/) and sets WEBHOOK_URL for this process, so the Telegram
# Trigger registers the public URL with Telegram. No other .env value is loaded.
#
# Execution retention (SPEC-005, NFR-08): n8n deletes stored executions older than
# -ExecutionsMaxAgeHours (default 720 h = 30 days) for the whole instance.
#
# Usage (from the repo root):  .\n8n-start.ps1
#   One-off short pruning test (SPEC-005 task L6):  .\n8n-start.ps1 -ExecutionsMaxAgeHours 1

param(
    [ValidateRange(1, 87600)]
    [int]$ExecutionsMaxAgeHours = 720
)

$ErrorActionPreference = 'Stop'
$envFile = Join-Path $PSScriptRoot '.env'

if (-not (Test-Path $envFile)) {
    Write-Error "No se encuentra .env en $PSScriptRoot"
    exit 1
}

$line = Get-Content $envFile | Where-Object { $_ -match '^\s*N8N_WEBHOOK_URL\s*=' } | Select-Object -Last 1
$url = if ($line) { ($line -split '=', 2)[1].Trim().Trim('"').Trim("'") } else { '' }

if (-not $url) {
    Write-Error 'N8N_WEBHOOK_URL no está definida en .env (ejemplo: https://<maquina>.<tailnet>.ts.net/)'
    exit 1
}
if ($url -notmatch '^https://') {
    Write-Error "N8N_WEBHOOK_URL debe empezar por https:// (Telegram solo acepta webhooks HTTPS): $url"
    exit 1
}
if (-not $url.EndsWith('/')) { $url += '/' }

if (-not (Get-Command n8n -ErrorAction SilentlyContinue)) {
    Write-Error 'No se encuentra el comando n8n. Instálalo con: npm install -g n8n@latest'
    exit 1
}

# Refuse to start if another process (usually an n8n already running) holds the port: n8n would
# fail with "port 5678 is already in use" and the running instance would keep its own settings,
# e.g. a different retention (SPEC-005 task L6).
$port = if ($env:N8N_PORT) { [int]$env:N8N_PORT } else { 5678 }
$listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    $owner = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    $who = if ($owner) { "$($owner.ProcessName) (PID $($owner.Id), arrancado $($owner.StartTime))" } else { "PID $($listener.OwningProcess)" }
    Write-Host "El puerto $port ya está ocupado por $who." -ForegroundColor Red
    Write-Host 'Probablemente ya hay un n8n en marcha, con su propia configuración (por ejemplo, otra retención).' -ForegroundColor Red
    Write-Host "Páralo (Ctrl+C en su consola o Stop-Process -Id $($listener.OwningProcess)) y vuelve a lanzar este script." -ForegroundColor Red
    exit 1
}

$env:WEBHOOK_URL = $url
# Keep the editor (and the MCP OAuth issuer/endpoints n8n derives from it) on localhost: only
# /webhook is published through Funnel, so OAuth must never point at the public host (D10).
$env:N8N_EDITOR_BASE_URL = 'http://localhost:5678/'
# Retention for this process only (SPEC-005 P10); other pruning settings keep n8n's defaults.
$env:EXECUTIONS_DATA_PRUNE = 'true'
$env:EXECUTIONS_DATA_MAX_AGE = "$ExecutionsMaxAgeHours"
Write-Host "Arrancando n8n con WEBHOOK_URL=$url y N8N_EDITOR_BASE_URL=$env:N8N_EDITOR_BASE_URL"
Write-Host "Retención de ejecuciones: EXECUTIONS_DATA_PRUNE=$env:EXECUTIONS_DATA_PRUNE EXECUTIONS_DATA_MAX_AGE=$env:EXECUTIONS_DATA_MAX_AGE (horas)"
if ($ExecutionsMaxAgeHours -ne 720) {
    Write-Host "AVISO: retención distinta de 720 h (30 días). Vuelve a arrancar con .\n8n-start.ps1 al terminar la prueba." -ForegroundColor Yellow
}
Write-Host 'Editor local: http://localhost:5678  (Ctrl+C para parar)'
n8n start
