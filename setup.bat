@echo off
chcp 65001 >nul
echo ========================================
echo   AirQRT - 初始化
echo ========================================
echo.

:: 检测Python
set PYTHON_CMD=
where py >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :found_python
)
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :found_python
)

echo 错误: 未找到Python，请先安装Python 3.8+
echo 下载地址: https://www.python.org/downloads/
pause
exit /b 1

:found_python
echo [1/3] 检测到Python:
%PYTHON_CMD% --version

echo.
echo [2/3] 安装依赖...
%PYTHON_CMD% -m pip install -r requirements.txt

echo.
echo [3/3] 创建目录...
if not exist "send_dir" mkdir send_dir
if not exist "received_files" mkdir received_files

echo.
echo ========================================
echo   初始化完成!
echo ========================================
echo.
echo 使用方法:
echo   发送: 双击 start_sender.bat
echo   接收: 双击 start_receiver.bat
echo.
pause
