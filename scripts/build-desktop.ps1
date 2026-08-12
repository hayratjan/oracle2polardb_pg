<#
.SYNOPSIS
  Oracle2PolarDB 桌面客户端 Windows 构建脚本
#>
[CmdletBinding()]
param(
  [switch]$Debug,
  [string]$Bundles = "",
  [string]$Target = ""
)

$ErrorActionPreference = "Stop"
$RootDir = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $RootDir

function Write-Log { param([string]$Msg) Write-Host "[build-desktop] $Msg" -ForegroundColor Cyan }
function Write-Warn { param([string]$Msg) Write-Host "[build-desktop] $Msg" -ForegroundColor Yellow }
function Die { param([string]$Msg) Write-Host "[build-desktop] 错误: $Msg" -ForegroundColor Red; exit 1 }

Write-Log "检测构建环境..."
foreach ($cmd in @("cargo", "pnpm")) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Die "未找到命令: $cmd" }
}

try { $null = cargo tauri --version 2>&1; $tauriOk = $LASTEXITCODE -eq 0 } catch { $tauriOk = $false }
if (-not $tauriOk) {
  Write-Log "未检测到 tauri-cli,正在安装..."
  cargo install tauri-cli --version "^2.0.0" --locked
  if ($LASTEXITCODE -ne 0) { Die "tauri-cli 安装失败" }
}

Write-Log "安装前端依赖..."
Push-Location "$RootDir\frontend"
try { pnpm install --frozen-lockfile; if ($LASTEXITCODE -ne 0) { pnpm install } } finally { Pop-Location }

Write-Log "构建前端 (Tauri 模式)..."
Push-Location "$RootDir\frontend"
try { pnpm build:tauri; if ($LASTEXITCODE -ne 0) { Die "前端构建失败" } } finally { Pop-Location }

$ResourcesDir = "$RootDir\src-tauri\resources\backend"
Write-Log "准备后端资源到 $ResourcesDir..."
if (Test-Path $ResourcesDir) { Remove-Item -Recurse -Force $ResourcesDir }
New-Item -ItemType Directory -Force -Path $ResourcesDir | Out-Null

function Copy-Backend { param([string]$Src, [string]$Dst)
  if (Test-Path $Src) { robocopy $Src $Dst /MIR /XD __pycache__ .pytest_cache /XF *.pyc /NFL /NDL /NJH /NJS /NC /NS /NP | Out-Null }
}

Copy-Item "$RootDir\manage.py" $ResourcesDir -ErrorAction SilentlyContinue
Copy-Item "$RootDir\requirements.txt" $ResourcesDir -ErrorAction SilentlyContinue
if (Test-Path "$RootDir\migration_app") { Copy-Backend "$RootDir\migration_app" "$ResourcesDir\migration_app" }
if (Test-Path "$RootDir\oracle2polardb_pg") { Copy-Backend "$RootDir\oracle2polardb_pg" "$ResourcesDir\oracle2polardb_pg" }
if (Test-Path "$RootDir\staticfiles") { Copy-Backend "$RootDir\staticfiles" "$ResourcesDir\staticfiles" }

@"
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=desktop-local-please-change-in-production
DATABASE_URL=sqlite:///oracle2polardb_desktop.db
ALLOWED_HOSTS=127.0.0.1,localhost
"@ | Out-File -Encoding utf8 -FilePath "$ResourcesDir\.env.production"

$tauriArgs = @("tauri", "build")
if ($Debug) { $tauriArgs += "--debug" }
if ($Target) { $tauriArgs += @("--target", $Target) }
if ($Bundles) { $tauriArgs += @("--bundles", $Bundles) }

Write-Log "执行: cargo $($tauriArgs -join ' ')"
& cargo @tauriArgs
if ($LASTEXITCODE -ne 0) { Die "cargo tauri build 失败" }

$OutputDir = "$RootDir\src-tauri\target\release"
if ($Target) { $OutputDir = "$RootDir\src-tauri\target\$Target\release" }
$BundleDir = "$OutputDir\bundle"

Write-Log "=========================================="
Write-Log "  构建完成"
Write-Log "=========================================="
if (Test-Path $BundleDir) {
  Write-Log "产物目录: $BundleDir"
  Get-ChildItem -Recurse -File -Include *.exe,*.msi -Path $BundleDir | ForEach-Object {
    Write-Log ("  - {0}  ({1:N1} MB)" -f $_.FullName.Substring($BundleDir.Length + 1), ($_.Length / 1MB))
  }
}
