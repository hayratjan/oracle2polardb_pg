#!/usr/bin/env bash
# Oracle2PolarDB 桌面客户端构建脚本 (macOS / Linux)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log()  { printf '\033[1;36m[build-desktop]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[build-desktop]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[build-desktop]\033[0m 错误: %s\n' "$*" >&2; exit 1; }

BUILD_MODE="release"
EXTRA_TARGETS=()
BUNDLES=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --debug) BUILD_MODE="debug"; shift ;;
    --target) EXTRA_TARGETS+=("$2"); shift 2 ;;
    --bundles) BUNDLES="$2"; shift 2 ;;
    --help|-h)
      cat <<'EOF'
用法: ./scripts/build-desktop.sh [选项]
选项:
  --debug            debug 构建(默认 release)
  --target <triple>  指定 Rust target
  --bundles <list>   指定打包格式(dmg/deb/rpm/appimage)
  --help             显示本帮助
EOF
      exit 0 ;;
    *) EXTRA_ARGS+=("$1"); shift ;;
  esac
done

require_cmd() { command -v "$1" >/dev/null 2>&1 || die "未找到命令「${1}」,请先安装。"; }
require_cmd cargo
require_cmd pnpm

if ! cargo tauri --version >/dev/null 2>&1; then
  log "未检测到 tauri-cli,正在安装..."
  cargo install tauri-cli --version "^2.0.0" --locked
fi

case "$(uname -s)" in
  Darwin)
    log "检测到 macOS"
    xcode-select -p >/dev/null 2>&1 || die "未安装 Xcode Command Line Tools: xcode-select --install" ;;
  Linux)
    log "检测到 Linux"
    pkg-config --exists webkit2gtk-4.1 2>/dev/null || warn "未检测到 webkit2gtk-4.1,请安装系统依赖" ;;
  *) die "本脚本仅支持 macOS / Linux,Windows 请使用 scripts/build-desktop.ps1" ;;
esac

log "安装前端依赖..."
(cd "$ROOT_DIR/frontend" && pnpm install --frozen-lockfile || pnpm install)

log "构建前端 (Tauri 模式)..."
(cd "$ROOT_DIR/frontend" && pnpm build:tauri)

RESOURCES_DIR="$ROOT_DIR/src-tauri/resources/backend"
log "准备后端资源到 ${RESOURCES_DIR}..."
rm -rf "$RESOURCES_DIR"
mkdir -p "$RESOURCES_DIR"

copy_backend() {
  local src="$1" dst="$2"
  [[ -d "$src" ]] && rsync -a --delete --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' "$src/" "$dst/"
}

cp "$ROOT_DIR/manage.py" "$RESOURCES_DIR/" 2>/dev/null || warn "manage.py 未找到"
cp "$ROOT_DIR/requirements.txt" "$RESOURCES_DIR/" 2>/dev/null || warn "requirements.txt 未找到"
copy_backend "$ROOT_DIR/migration_app" "$RESOURCES_DIR/migration_app"
copy_backend "$ROOT_DIR/oracle2polardb_pg" "$RESOURCES_DIR/oracle2polardb_pg"
[[ -d "$ROOT_DIR/staticfiles" ]] && copy_backend "$ROOT_DIR/staticfiles" "$RESOURCES_DIR/staticfiles"

cat > "$RESOURCES_DIR/.env.production" <<'EOF'
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=desktop-local-please-change-in-production
DATABASE_URL=sqlite:///oracle2polardb_desktop.db
ALLOWED_HOSTS=127.0.0.1,localhost
EOF

log "后端资源准备完成 ($(du -sh "$RESOURCES_DIR" | cut -f1))"

TAURI_ARGS=()
[[ "$BUILD_MODE" == "debug" ]] && TAURI_ARGS+=("--debug")
for t in "${EXTRA_TARGETS[@]}"; do TAURI_ARGS+=("--target" "$t"); done
[[ -n "$BUNDLES" ]] && TAURI_ARGS+=("--bundles" "$BUNDLES")
TAURI_ARGS+=("${EXTRA_ARGS[@]}")

log "执行: cargo tauri build ${TAURI_ARGS[*]}"
cargo tauri build "${TAURI_ARGS[@]}"

OUTPUT_DIR="$ROOT_DIR/src-tauri/target/release"
[[ ${#EXTRA_TARGETS[@]} -gt 0 ]] && OUTPUT_DIR="$ROOT_DIR/src-tauri/target/${EXTRA_TARGETS[0]}/release"

log "=========================================="
log "  构建完成"
log "=========================================="
if [[ -d "$OUTPUT_DIR/bundle" ]]; then
  log "产物目录: $OUTPUT_DIR/bundle"
  find "$OUTPUT_DIR/bundle" -type f \( -name "*.dmg" -o -name "*.app" -o -name "*.deb" -o -name "*.rpm" -o -name "*.AppImage" \) -print0 |
    while IFS= read -r -d '' f; do
      printf '   - %s  (%s)\n' "${f#$OUTPUT_DIR/bundle/}" "$(du -h "$f" | cut -f1)"
    done
fi
