@echo off
echo ���ڼ��Python������������...

REM ���Python�Ƿ��Ѱ�װ
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo δ��⵽Python���밲װPython 3.7����߰汾
    pause
    exit /b
)

REM ����������Ƿ��Ѱ�װ
echo �������...
pip show PyQt5 >nul 2>&1
if %errorlevel% neq 0 (
    echo ���ڰ�װ��Ҫ��������...
    pip install PyQt5>=5.15.0 requests>=2.25.0 psutil>=5.8.0
    pip install "PyQt-Fluent-Widgets[full]" -i https://pypi.org/simple/
    if %errorlevel% neq 0 (
        echo ������װʧ�ܣ��볢���ֶ���װ����: pip install -r requirements.txt
        pause
        exit /b
    )
)

REM ����Ӧ�ó���
echo ����Ӧ�ó���...
python main.py

pause