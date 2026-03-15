$ErrorActionPreference = 'Stop'

Write-Host 'Checking MongoDB listener on 127.0.0.1:27017...'
$mongoListening = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalAddress -eq '127.0.0.1' -and $_.LocalPort -eq 27017 }

if (-not $mongoListening) {
    $mongodCandidates = @(
        (Join-Path $PSScriptRoot '..\mongodb\mongodb-win32-x86_64-windows-7.0.12\bin\mongod.exe'),
        (Join-Path $PSScriptRoot '..\mongodb\bin\mongod.exe')
    )
    $mongodPath = $mongodCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    $mongoDataPath = Join-Path $PSScriptRoot '..\mongodb\data'
    if (-not (Test-Path $mongoDataPath)) {
        New-Item -ItemType Directory -Path $mongoDataPath | Out-Null
    }
    if ($mongodPath) {
        Write-Host 'Starting MongoDB...'
        Start-Process -FilePath $mongodPath -ArgumentList "--dbpath `"$mongoDataPath`" --bind_ip 127.0.0.1 --port 27017" | Out-Null
        Start-Sleep -Seconds 2
    } else {
        Write-Warning "mongod.exe not found in expected MongoDB folders"
    }
}

Write-Host 'Starting FastAPI backend on 127.0.0.1:8000...'
$venvPython = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    throw "Python virtual environment not found at $venvPython"
}

Start-Process -FilePath $venvPython -ArgumentList '-m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload' -WorkingDirectory (Join-Path $PSScriptRoot '..') | Out-Null

Write-Host 'Waiting for API health...'
$healthy = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $resp = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -Method Get -TimeoutSec 3
        if ($resp.status -eq 'ok') {
            $healthy = $true
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if ($healthy) {
    Write-Host 'API is healthy at http://127.0.0.1:8000'
} else {
    Write-Warning 'API did not become healthy in time. Check backend logs.'
}
