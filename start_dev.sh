#!/usr/bin/env bash
# =============================================================================
# Oracle → PolarDB 开发环境一键启动脚本（macOS / Linux）
# 同时启动 Django 后端 (默认 8000) 与 Vue/Vite 前端 (默认 5173)
# 用法: ./start_dev.sh [--migrate] [--install] [--celery] [--help]
# Windows 请使用 start_dev.bat 或 start_dev.ps1
# =============================================================================

set -euo pipefail

# 项目根目录（脚本所在目录）
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# 可覆盖的端口与地址
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

# 子进程 PID 列表，用于退出时统一清理
PIDS=()

# 是否执行 migrate / 安装依赖 / 启动 Celery Worker
RUN_MIGRATE=false
RUN_INSTALL=false
RUN_CELERY=false

# -----------------------------------------------------------------------------
# 工具函数
# -----------------------------------------------------------------------------

log() {
  printf '\033[1;36m[start_dev]\033[0m %s\n' "$*"
}

warn() {
  printf '\033[1;33m[start_dev]\033[0m %s\n' "$*" >&2
}

die() {
  printf '\033[1;31m[start_dev]\033[0m 错误: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
用法: ./start_dev.sh [选项]

选项:
  --migrate   启动前执行 uv run manage.py migrate
  --install   启动前安装后端与前端依赖
  --celery    若已配置 CELERY_BROKER_URL，额外启动 Celery Worker
  --help      显示本帮助

环境变量:
  BACKEND_HOST   后端监听地址（默认 0.0.0.0）
  BACKEND_PORT   后端端口（默认 8000）
  FRONTEND_PORT  前端端口（默认 5173，需与 frontend/vite.config.ts 一致）
  CELERY_BROKER_URL  设置后可用 --celery 启动异步迁移 Worker

示例:
  ./start_dev.sh
  ./start_dev.sh --migrate --install
  CELERY_BROKER_URL=redis://127.0.0.1:6379/0 ./start_dev.sh --celery
EOF
}

require_cmd() {
  local name="$1"
  command -v "$name" >/dev/null 2>&1 || die "未找到命令「${name}」，请先安装后再运行本脚本。"
}

# 退出时终止所有子进程
cleanup() {
  if ((${#PIDS[@]} == 0)); then
    return
  fi
  echo ""
  log "正在停止服务 (PID: ${PIDS[*]})..."
  for pid in "${PIDS[@]}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  # 等待子进程结束，避免僵尸进程
  for pid in "${PIDS[@]}"; do
    wait "$pid" 2>/dev/null || true
  done
  log "已退出。"
}

trap cleanup EXIT INT TERM

start_process() {
  local label="$1"
  shift
  log "启动 ${label}..."
  "$@" &
  PIDS+=("$!")
}

# -----------------------------------------------------------------------------
# 参数解析
# -----------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
  case "$1" in
    --migrate)
      RUN_MIGRATE=true
      shift
      ;;
    --install)
      RUN_INSTALL=true
      shift
      ;;
    --celery)
      RUN_CELERY=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      die "未知参数: $1（使用 --help 查看说明）"
      ;;
  esac
done

# -----------------------------------------------------------------------------
# 环境检查
# -----------------------------------------------------------------------------

require_cmd uv
require_cmd pnpm

if [[ ! -f "$ROOT_DIR/manage.py" ]]; then
  die "未在项目根目录找到 manage.py，请确认脚本位置正确。"
fi

if [[ ! -d "$ROOT_DIR/frontend" ]]; then
  die "未找到 frontend 目录。"
fi

# -----------------------------------------------------------------------------
# 可选：安装依赖
# -----------------------------------------------------------------------------

if [[ "$RUN_INSTALL" == true ]]; then
  log "安装后端依赖..."
  if [[ -f "$ROOT_DIR/requirements.txt" ]]; then
    uv pip install -r requirements.txt
  else
    uv sync
  fi
  log "安装前端依赖..."
  (cd "$ROOT_DIR/frontend" && pnpm install)
fi

# -----------------------------------------------------------------------------
# 可选：数据库迁移
# -----------------------------------------------------------------------------

if [[ "$RUN_MIGRATE" == true ]]; then
  log "执行数据库迁移..."
  uv run manage.py migrate --noinput
fi

# -----------------------------------------------------------------------------
# 启动服务
# -----------------------------------------------------------------------------

log "=========================================="
log "  Oracle → PolarDB 开发环境"
log "  后端: http://127.0.0.1:${BACKEND_PORT}"
log "  前端: http://127.0.0.1:${FRONTEND_PORT}"
log "  按 Ctrl+C 停止全部服务"
log "=========================================="

# Django 开发服务器
start_process "后端 (Django)" \
  uv run manage.py runserver "${BACKEND_HOST}:${BACKEND_PORT}"

# Vite 开发服务器（API 通过 vite.config.ts 代理到后端）
start_process "前端 (Vite)" \
  bash -c "cd \"${ROOT_DIR}/frontend\" && exec pnpm dev --host --port \"${FRONTEND_PORT}\""

# 可选：Celery Worker（需配置消息队列）
if [[ "$RUN_CELERY" == true ]]; then
  if [[ -z "${CELERY_BROKER_URL:-}" ]]; then
    warn "未设置 CELERY_BROKER_URL，跳过 Celery Worker。"
    warn "示例: export CELERY_BROKER_URL=redis://127.0.0.1:6379/0"
  else
    start_process "Celery Worker" \
      uv run celery -A oracle2polardb_pg worker -l info
  fi
fi

# 阻塞直到任一子进程退出（通常为用户 Ctrl+C）
wait -n 2>/dev/null || wait
