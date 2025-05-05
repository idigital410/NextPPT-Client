@echo off
echo 正在检查Python环境和依赖项...

REM 检查Python是否已安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 未检测到Python，请安装Python 3.7或更高版本
    pause
    exit /b
)

REM 检查依赖项是否已安装
echo 检查依赖...
pip show PyQt5 >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装必要的依赖项...
    pip install PyQt5>=5.15.0 requests>=2.25.0 psutil>=5.8.0
    pip install "PyQt-Fluent-Widgets[full]" -i https://pypi.org/simple/
    if %errorlevel% neq 0 (
        echo 依赖安装失败，请尝试手动安装依赖: pip install -r requirements.txt
        pause
        exit /b
    )
)

REM 启动应用程序
echo 启动应用程序...
python main.py

pause