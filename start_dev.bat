@echo off
REM =============================================================================
REM Oracle → PolarDB 开发环境一键启动（Windows 入口）
REM 双击运行或在 cmd 中执行: start_dev.bat [参数]
REM 参数会原样传递给 start_dev.ps1，例如: start_dev.bat -Migrate -Install
REM =============================================================================

setlocal
cd /d "%~dp0"

where powershell >nul 2>&1
if errorlevel 1 (
    echo [start_dev] 错误: 未找到 PowerShell，无法启动。
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_dev.ps1" %*
set EXIT_CODE=%ERRORLEVEL%
endlocal & exit /b %EXIT_CODE%
