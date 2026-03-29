#Requires -Version 5.1
# Stops old Streamlit/API listeners on project ports, then starts API (8000) + Streamlit (8888).
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Root) { $Root = (Get-Location).Path }

function Stop-ListenersOnPorts {
    param([int[]]$Ports)
    # Windows: several uvicorn --reload / old runs can leave multiple LISTENING PIDs on one port.
    # Get-NetTCPConnection often returns only one; netstat -ano catches all.
    foreach ($port in $Ports) {
        for ($round = 0; $round -lt 12; $round++) {
            $found = $false
            $lines = @(netstat -ano | Select-String -Pattern ":$port\s+.*LISTENING")
            foreach ($line in $lines) {
                if ($line.Line -match '\s+(\d+)\s*$') {
                    $procId = [int]$Matches[1]
                    if ($procId -gt 0) {
                        $found = $true
                        Write-Host "Stopping PID $procId (port $port)..."
                        & cmd /c "taskkill /F /PID $procId" 2>$null
                    }
                }
            }
            if (-not $found) { break }
            Start-Sleep -Milliseconds 400
        }
    }
}

Write-Host "Stopping previous listeners (Streamlit + API on project ports)..."
$ports = @(8000, 8501, 8502, 8510, 8520, 8585, 8888)
Stop-ListenersOnPorts $ports
Start-Sleep -Milliseconds 600
Stop-ListenersOnPorts $ports
Start-Sleep -Milliseconds 400
Write-Host "Ports cleared. Starting fresh uvicorn (from backend/) + Streamlit (8888)."

$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"

if (-not (Test-Path $BackendDir)) {
    Write-Error "Backend folder not found: $BackendDir"
    exit 1
}
if (-not (Test-Path $FrontendDir)) {
    Write-Error "Frontend folder not found: $FrontendDir"
    exit 1
}

Write-Host "Starting API: http://127.0.0.1:8000 ..."
Start-Process powershell -WorkingDirectory $BackendDir -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location `"$BackendDir`"; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
)

Start-Sleep -Seconds 2

Write-Host "Starting Streamlit: http://127.0.0.1:8888 ..."
Start-Process powershell -WorkingDirectory $FrontendDir -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location `"$FrontendDir`"; python -m streamlit run app.py --server.port 8888"
)

Write-Host ""
Write-Host "Frontend: http://127.0.0.1:8888"
Write-Host "API docs: http://127.0.0.1:8000/docs"
Write-Host "If Risk Map shows 404, open http://127.0.0.1:8000/openapi.json — paths must include 'inland'."
Write-Host "If 404 persists: run netstat -ano ^| findstr :8000 — only one LISTENING PID should own :8000; close extra terminals running uvicorn."
Write-Host "(Two new PowerShell windows were opened; close them to stop the servers.)"
