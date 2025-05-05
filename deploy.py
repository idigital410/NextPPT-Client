import os
import sys

# 版本信息
VERSION = "1.0.0"
YEAR = "2025"
AUTHOR = "Client"

if sys.platform == "win32":
    args = [
        'nuitka',
        '--standalone',  # 独立模式，包含所有依赖
        '--windows-console-mode=disable',  # 禁用控制台窗口
        '--plugin-enable=pyqt5',  # 启用PyQt5插件
        '--include-package=qfluentwidgets',  # 包含PyQt-Fluent-Widgets包
        '--assume-yes-for-downloads',  # 自动下载所需组件
        '--mingw64',  # 使用MinGW编译器
        '--show-memory',  # 显示内存使用情况
        '--show-progress',  # 显示进度
        '--windows-icon-from-ico=../1.png',  # 使用指定的图标
        '--company-name="Client"',
        '--product-name="Client Downloader"',
        f'--file-version={VERSION}',
        f'--product-version={VERSION}',
        '--file-description="Client Downloader"',
        f'--copyright="Copyright(C) {YEAR} {AUTHOR}"',
        '--output-dir=dist',  # 输出目录
        'main.py',  # 主程序文件
    ]
else:
    print("当前仅支持Windows平台打包")
    sys.exit(1)

# 执行打包命令
print("开始打包...")
print(" ".join(args))
os.system(' '.join(args))
print("打包完成，请查看dist目录")