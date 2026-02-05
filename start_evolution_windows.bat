@echo off
REM Windows 专用进化启动脚本
REM 使用 pythonw.exe 在后台运行，不会被 PowerShell 中断

echo ====================================================================
echo 原智 (YuanZhi) - 启动自动进化
echo ====================================================================
echo.

REM 检查 Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Python，请确保已安装 Python 并添加到 PATH
    pause
    exit /b 1
)

REM 启动进化进程
echo [启动] 正在后台启动进化进程...
start /B pythonw.exe goal_evolution.py
timeout /t 2 >nul

REM 检查进程
tasklist /FI "IMAGENAME eq pythonw.exe" 2>NUL | find /I "pythonw.exe" >NUL
if %ERRORLEVEL% EQU 0 (
    echo [成功] 进化进程已启动
    echo.
    echo 查看进度：
    echo   - 日志文件: prokaryote_agent\log\prokaryote.log
    echo   - 目标文件: evolution_goals.md
    echo.
    echo 停止进化：
    echo   taskkill /IM pythonw.exe /F
) else (
    echo [失败] 进化进程启动失败
    pause
    exit /b 1
)

echo.
echo ====================================================================
pause
