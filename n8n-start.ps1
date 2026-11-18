# Starts n8n for the LifeCenter Telegram demo (CHG-001, specs/003-n8n-migration/plan.md).
#
# Reads ONLY N8N_WEBHOOK_URL from .env (the public Tailscale Funnel URL, e.g.
# https://<machine>.<tailnet>.ts.net/) and sets WEBHOOK_URL for this process, so the Telegram
# Trigger registers the public URL with Telegram. No other .env value is loaded.
#
# Usage (from the repo root):  .\n8n-start.ps1

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

$env:WEBHOOK_URL = $url
# Keep the editor (and the MCP OAuth issuer/endpoints n8n derives from it) on localhost: only
# /webhook is published through Funnel, so OAuth must never point at the public host (D10).
$env:N8N_EDITOR_BASE_URL = 'http://localhost:5678/'
Write-Host "Arrancando n8n con WEBHOOK_URL=$url y N8N_EDITOR_BASE_URL=$env:N8N_EDITOR_BASE_URL"
Write-Host 'Editor local: http://localhost:5678  (Ctrl+C para parar)'
n8n start
