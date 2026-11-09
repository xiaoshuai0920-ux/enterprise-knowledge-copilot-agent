Set-Location (Join-Path $PSScriptRoot "..")

function Test-DockerDaemon {
    # 用 cmd 包一层，避免 PowerShell 把原生 stderr 当成异常
    cmd /c "docker info >nul 2>&1"
    return ($LASTEXITCODE -eq 0)
}

# 1. 检查 docker CLI
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] 未找到 docker 命令，请先安装 Docker Desktop。" -ForegroundColor Red
    exit 1
}

# 2. 检查 Docker 守护进程，未运行则尝试拉起 Docker Desktop
if (-not (Test-DockerDaemon)) {
    Write-Host "[WARN] Docker 守护进程未运行。" -ForegroundColor Yellow
    $desktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $desktop) {
        Write-Host "正在启动 Docker Desktop ..."
        Start-Process $desktop
        Write-Host "等待 Docker 引擎就绪（最长 180 秒）..."
        $deadline = (Get-Date).AddSeconds(180)
        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds 3
            if (Test-DockerDaemon) { break }
        }
    }
    if (-not (Test-DockerDaemon)) {
        Write-Host "[ERROR] Docker 仍未就绪。请手动启动 Docker Desktop，等鲸鱼图标变绿后重试。" -ForegroundColor Red
        exit 1
    }
    Write-Host "Docker 已就绪。"
}

# 3. 准备 .env
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

# 4. 构建并启动
docker compose up --build -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] docker compose 启动失败，请查看上方日志。" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Frontend: http://localhost:3000"
Write-Host "Swagger:  http://localhost:8000/docs"
