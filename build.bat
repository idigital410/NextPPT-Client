@echo off
echo 正在准备打包环境...

REM 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未检测到Python环境，请安装Python并确保已添加到PATH中
    pause
    exit /b 1
)

REM 检查Nuitka是否已安装
pip show nuitka >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装Nuitka打包工具...
    pip install nuitka
    if %errorlevel% neq 0 (
        echo 错误: Nuitka安装失败
        pause
        exit /b 1
    )
)

REM 检查PyQt-Fluent-Widgets是否已安装
pip show PyQt-Fluent-Widgets >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装PyQt-Fluent-Widgets...
    pip install "PyQt-Fluent-Widgets[full]" -i https://pypi.org/simple/
    if %errorlevel% neq 0 (
        echo 错误: PyQt-Fluent-Widgets安装失败
        pause
        exit /b 1
    )
)

REM 检查imageio是否已安装（用于处理PNG图标）
pip show imageio >nul 2>&1
if %errorlevel% neq 0 (
    echo 正在安装imageio库（用于处理PNG图标）...
    pip install imageio
    if %errorlevel% neq 0 (
        echo 错误: imageio安装失败
        pause
        exit /b 1
    )
)

echo 开始打包程序...
python deploy.py

if %errorlevel% neq 0 (
    echo 打包过程中出现错误，请检查日志
) else (
    echo 打包完成！程序已生成在dist目录中
)

pause