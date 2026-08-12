#!/usr/bin/env bash
# 生成 Tauri 桌面应用图标
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

log()  { printf '\033[1;36m[gen-icons]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[gen-icons]\033[0m 错误: %s\n' "$*" >&2; exit 1; }

ICONS_DIR="$ROOT_DIR/src-tauri/icons"
mkdir -p "$ICONS_DIR"

SOURCE_PNG=""
if [[ $# -ge 1 ]]; then
  SOURCE_PNG="$1"
elif [[ -f "$ROOT_DIR/frontend/src/assets/logo.png" ]]; then
  SOURCE_PNG="$ROOT_DIR/frontend/src/assets/logo.png"
elif [[ -f "$ROOT_DIR/frontend/src/assets/logo.svg" ]]; then
  if ! command -v convert >/dev/null 2>&1; then
    die "未找到 ImageMagick(convert),请安装或提供 PNG 源图: $0 <源图.png>"
  fi
  SOURCE_PNG="$ICONS_DIR/_source_1024.png"
  log "从 SVG 渲染源图: $SOURCE_PNG"
  convert -background none -resize 1024x1024 "$ROOT_DIR/frontend/src/assets/logo.svg" "$SOURCE_PNG"
else
  die "未找到源图,请提供: $0 <源图.png>(建议 1024x1024 PNG)"
fi

[[ -f "$SOURCE_PNG" ]] || die "源图不存在: $SOURCE_PNG"

if ! cargo tauri --version >/dev/null 2>&1; then
  log "未检测到 tauri-cli,正在安装..."
  cargo install tauri-cli --version "^2.0.0" --locked
fi

log "使用源图: $SOURCE_PNG"
log "生成图标到: $ICONS_DIR"
cargo tauri icon "$SOURCE_PNG" --output "$ICONS_DIR"

log "=========================================="
log "  图标生成完成"
log "=========================================="
ls -lh "$ICONS_DIR" | grep -v '^total' | sed 's/^/  /'

rm -f "$ICONS_DIR/_source_1024.png" 2>/dev/null || true
