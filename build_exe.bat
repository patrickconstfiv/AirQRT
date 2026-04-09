@echo off
chcp 65001 >nul
echo ========================================
echo   AirQRT - 打包为 EXE
echo ========================================
echo.

:: 检测 Python
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
echo 错误: 未找到Python
pause
exit /b 1

:found_python
echo [1/3] 安装 PyInstaller...
%PYTHON_CMD% -m pip install pyinstaller

echo.
echo [2/3] 安装依赖...
%PYTHON_CMD% -m pip install -r requirements.txt

echo.
echo [3/3] 打包中...
%PYTHON_CMD% -m PyInstaller --onefile --windowed --name "AirQRT" ^
    --icon=icon.ico ^
    --hidden-import=windnd ^
    app.py

echo.
if exist "dist\AirQRT.exe" (
    echo ========================================
    echo   打包成功!
    echo   输出文件: dist\AirQRT.exe
    echo ========================================
) else (
    echo ========================================
    echo   打包可能失败，请检查上方错误信息
    echo ========================================
)
echo.
pause
