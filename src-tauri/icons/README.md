# Tauri 应用图标

此目录存放桌面应用打包所需的图标文件。

## 必需文件

| 文件 | 用途 |
|------|------|
| `32x32.png` | Linux 小图标 |
| `128x128.png` | Linux 标准图标 |
| `128x128@2x.png` | Linux 高分屏 |
| `icon.icns` | macOS 应用图标 |
| `icon.ico` | Windows 应用图标 |
| `icon.png` | 通用源图标(1024x1024) |

## 生成方式

```bash
# 使用脚本(推荐)
./scripts/generate-icons.sh path/to/your-logo.png

# 或直接使用 tauri-cli
cargo install tauri-cli --version "^2.0.0"
cargo tauri icon path/to/source.png --output src-tauri/icons
```

首次构建前必须执行一次,否则 `cargo tauri build` 会因找不到图标失败。
