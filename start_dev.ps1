# =============================================================================
# Oracle → PolarDB 开发环境一键启动脚本（Windows / PowerShell）
# 同时启动 Django 后端 (默认 8000) 与 Vue/Vite 前端 (默认 5173)
# 用法: .\start_dev.ps1 [-Migrate] [-Install] [-Celery] [-Beat] [-Help]
# =============================================================================

param(
    [switch]$Migrate,
    [switch]$Install,
    [switch]$Celery,
    [switch]$Beat,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

# 项目根目录（脚本所在目录）
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

# 可覆盖的端口与地址
$BackendHost = if ($env:BACKEND_HOST) { $env:BACKEND_HOST } else { "0.0.0.0" }
$BackendPort = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8000" }
$FrontendPort = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "5173" }

# 子进程列表，退出时统一清理
$Script:ChildProcesses = @()

function Write-Log {
    param([string]$Message)
    Write-Host "[start_dev] $Message" -ForegroundColor Cyan
}

function Write-WarnMsg {
    param([string]$Message)
    Write-Host "[start_dev] $Message" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Message)
    Write-Host "[start_dev] 错误: $Message" -ForegroundColor Red
    exit 1
}

function Show-Usage {
    @"
用法: .\start_dev.ps1 [选项]

选项:
  -Migrate    启动前执行 uv run manage.py migrate
  -Install    启动前安装后端与前端依赖
  -Celery     若已配置 CELERY_BROKER_URL，额外启动 Celery Worker
  -Help       显示本帮助

环境变量:
  BACKEND_HOST       后端监听地址（默认 0.0.0.0）
  BACKEND_PORT       后端端口（默认 8000）
  FRONTEND_PORT      前端端口（默认 5173，需与 frontend/vite.config.ts 一致）
  CELERY_BROKER_URL  设置后可用 -Celery 启动异步迁移 Worker

示例:
  .\start_dev.ps1
  .\start_dev.ps1 -Migrate -Install
  `$env:CELERY_BROKER_URL='redis://127.0.0.1:6379/0'; .\start_dev.ps1 -Celery
"@
}

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Stop-AllChildren {
    if ($Script:ChildProcesses.Count -eq 0) { return }
    Write-Host ""
    Write-Log "正在停止服务..."
    foreach ($proc in $Script:ChildProcesses) {
        if ($proc -and -not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Log "已退出。"
}

function Start-DevProcess {
    param(
        [string]$Label,
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory = $RootDir
    )
    Write-Log "启动 ${Label}..."
    $proc = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -PassThru `
        -NoNewWindow
    $Script:ChildProcesses += $proc
    return $proc
}

function Resolve-PnpmCommand {
    # Windows 上 pnpm 多为 .cmd 包装，优先查找可执行文件
    if (Test-CommandExists "pnpm.cmd") { return "pnpm.cmd" }
    if (Test-CommandExists "pnpm") { return "pnpm" }
    return $null
}

if ($Help) {
    Show-Usage
    exit 0
}

# Ctrl+C 或窗口关闭时清理子进程
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Stop-AllChildren } | Out-Null

try {
    if (-not (Test-CommandExists "uv")) {
        Write-Err "未找到命令「uv」，请先安装后再运行本脚本。"
    }

    $pnpmCmd = Resolve-PnpmCommand
    if (-not $pnpmCmd) {
        Write-Err "未找到命令「pnpm」，请先安装后再运行本脚本。"
    }

    if (-not (Test-Path (Join-Path $RootDir "manage.py"))) {
        Write-Err "未在项目根目录找到 manage.py，请确认脚本位置正确。"
    }

    if (-not (Test-Path (Join-Path $RootDir "frontend"))) {
        Write-Err "未找到 frontend 目录。"
    }

    if ($Install) {
        Write-Log "安装后端依赖..."
        if (Test-Path (Join-Path $RootDir "requirements.txt")) {
            & uv pip install -r requirements.txt
        } else {
            & uv sync
        }
        Write-Log "安装前端依赖..."
        Push-Location (Join-Path $RootDir "frontend")
        try {
            & $pnpmCmd install
        } finally {
            Pop-Location
        }
    }

    if ($Migrate) {
        Write-Log "执行数据库迁移..."
        & uv run manage.py migrate --noinput
    }

    Write-Log "=========================================="
    Write-Log "  Oracle → PolarDB 开发环境"
    Write-Log "  后端: http://127.0.0.1:${BackendPort}"
    Write-Log "  前端: http://127.0.0.1:${FrontendPort}"
    Write-Log "  按 Ctrl+C 停止全部服务"
    Write-Log "=========================================="

    # Django 开发服务器
    Start-DevProcess `
        -Label "后端 (Django)" `
        -FilePath "uv" `
        -ArgumentList @("run", "manage.py", "runserver", "${BackendHost}:${BackendPort}")

    # Vite 开发服务器（API 通过 vite.config.ts 代理到后端）
    Start-DevProcess `
        -Label "前端 (Vite)" `
        -FilePath $pnpmCmd `
        -ArgumentList @("dev", "--host", "--port", $FrontendPort) `
        -WorkingDirectory (Join-Path $RootDir "frontend")

    # 可选：Celery Worker（需配置消息队列）
    if ($Celery) {
        if (-not $env:CELERY_BROKER_URL) {
            Write-WarnMsg "未设置 CELERY_BROKER_URL，跳过 Celery Worker。"
            Write-WarnMsg "示例: `$env:CELERY_BROKER_URL='redis://127.0.0.1:6379/0'"
        } else {
            Start-DevProcess `
                -Label "Celery Worker" `
                -FilePath "uv" `
                -ArgumentList @("run", "celery", "-A", "oracle2polardb_pg", "worker", "-l", "info")
            if ($Beat) {
                Start-DevProcess `
                    -Label "Celery Beat" `
                    -FilePath "uv" `
                    -ArgumentList @("run", "celery", "-A", "oracle2polardb_pg", "beat", "-l", "info", "--scheduler", "django_celery_beat.schedulers:DatabaseScheduler")
            } else {
                Write-WarnMsg "未启动 Celery Beat；定时增量需使用 -Beat 或单独运行 celery beat。"
            }
        }
    }

    # 阻塞直到任一子进程退出（通常为用户 Ctrl+C）
    while ($true) {
        foreach ($proc in $Script:ChildProcesses) {
            if ($proc.HasExited) {
                if ($proc.ExitCode -ne 0) {
                    Write-WarnMsg "进程 PID $($proc.Id) 异常退出，退出码: $($proc.ExitCode)"
                }
                exit $proc.ExitCode
            }
        }
        Start-Sleep -Milliseconds 500
    }
}
finally {
    Stop-AllChildren
}
