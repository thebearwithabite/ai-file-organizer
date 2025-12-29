# AI File Organizer: Windows Powerhouse Setup Script
# This script prepares your Windows 5090 machine to act as a worker for the AI File Organizer.

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting AI File Organizer: Windows Powerhouse Setup" -ForegroundColor Cyan

# --- Robust Path Detection ---
# Adding common installation paths to the current session's PATH
$commonPaths = @(
    "C:\Program Files\Tailscale",
    "C:\Program Files\Ollama",
    "$env:LOCALAPPDATA\Programs\Ollama",
    "C:\Program Files\Git\cmd",
    "C:\Program Files\Git\bin"
)

foreach ($path in $commonPaths) {
    if ((Test-Path $path) -and ($env:PATH -notlike "*$path*")) {
        $env:PATH = "$path;$env:PATH"
    }
}

# 1. Check for Tailscale
if (-not (Get-Command tailscale -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️ Tailscale not found. Please install it from https://tailscale.com" -ForegroundColor Yellow
} else {
    $tsIp = tailscale ip -4
    Write-Host "✅ Tailscale is active. Your Windows IP is: $tsIp" -ForegroundColor Green
}

# 2. Check for Ollama
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️ Ollama not found. Please install it from https://ollama.com" -ForegroundColor Yellow
} else {
    Write-Host "✅ Ollama found. Ensuring models are available..." -ForegroundColor Green
    # Pull the requested vision model
    ollama pull qwen2.5-vl:7b
}

# 3. Setup MCP Bridge for Resolve
Write-Host "🏗️ Setting up Resolve MCP Bridge..." -ForegroundColor Cyan
$bridgeDir = "$HOME\Documents\AI_Organizer_Bridge"
if (-not (Test-Path $bridgeDir)) {
    New-Item -Path $bridgeDir -ItemType Directory
}

# Clone the MCP server if not exists
if (-not (Test-Path "$bridgeDir\davinci-resolve-mcp")) {
    Set-Location $bridgeDir
    # Try to find git if Get-Command fails
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "⚠️ Git not found in PATH. Please install Git from https://git-scm.com" -ForegroundColor Yellow
    } else {
        git clone https://github.com/samuelgursky/davinci-resolve-mcp.git
    }
}

# 4. Instructions for Resolve
Write-Host ""
Write-Host "🎯 FINAL STEPS:" -ForegroundColor Yellow
Write-Host "1. Open DaVinci Resolve on this machine."
Write-Host "2. Go to Preferences -> System -> General -> External Scripting -> Set to 'Local'."
Write-Host "3. In a terminal, run the MCP server in SSE mode:" -ForegroundColor Gray
Write-Host "   python `"$bridgeDir\davinci-resolve-mcp\src\resolve_mcp_server.py`" --transport sse" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ SETUP COMPLETE. Send the Tailscale IP ($tsIp) to the Mac!" -ForegroundColor Green
