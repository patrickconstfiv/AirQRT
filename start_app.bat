@echo off
chcp 65001 >nul

:: 尝试不同的Python命令
where py >nul 2>&1
if %errorlevel% equ 0 (
    py app.py
    goto :end
)

where python >nul 2>&1
if %errorlevel% equ 0 (
    python app.py
    goto :end
)

echo 错误: 未找到Python
echo 请先运行 setup.bat 安装环境
pause

:end
