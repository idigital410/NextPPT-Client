@echo off
echo ����׼���������...

REM ���Python����
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ����: δ��⵽Python�������밲װPython��ȷ������ӵ�PATH��
    pause
    exit /b 1
)

REM ���Nuitka�Ƿ��Ѱ�װ
pip show nuitka >nul 2>&1
if %errorlevel% neq 0 (
    echo ���ڰ�װNuitka�������...
    pip install nuitka
    if %errorlevel% neq 0 (
        echo ����: Nuitka��װʧ��
        pause
        exit /b 1
    )
)

REM ���PyQt-Fluent-Widgets�Ƿ��Ѱ�װ
pip show PyQt-Fluent-Widgets >nul 2>&1
if %errorlevel% neq 0 (
    echo ���ڰ�װPyQt-Fluent-Widgets...
    pip install "PyQt-Fluent-Widgets[full]" -i https://pypi.org/simple/
    if %errorlevel% neq 0 (
        echo ����: PyQt-Fluent-Widgets��װʧ��
        pause
        exit /b 1
    )
)

REM ���imageio�Ƿ��Ѱ�װ�����ڴ���PNGͼ�꣩
pip show imageio >nul 2>&1
if %errorlevel% neq 0 (
    echo ���ڰ�װimageio�⣨���ڴ���PNGͼ�꣩...
    pip install imageio
    if %errorlevel% neq 0 (
        echo ����: imageio��װʧ��
        pause
        exit /b 1
    )
)

echo ��ʼ�������...
python deploy.py

if %errorlevel% neq 0 (
    echo ��������г��ִ���������־
) else (
    echo �����ɣ�������������distĿ¼��
)

pause