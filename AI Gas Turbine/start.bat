@echo off
chcp 65001 >nul
title 9F Power Plant Monitoring System

echo =======================================================
echo       9F Power Plant Monitoring System - Launcher
echo =======================================================
echo.

REM Set project directories
set "PROJECT_ROOT=%~dp0"
set "OLLAMA_DIR=%PROJECT_ROOT%ollama"
set "GUI_DIR=%PROJECT_ROOT%GUI"

:MAIN_MENU
cls
echo =======================================================
echo                    9F Power Plant
echo =======================================================
echo.
echo 请选择启动模式:
echo 1. 命令行模式 (原有系统)
echo 2. GUI图形界面 (新系统)
echo 3. 启动数据采集
echo 4. 启动DeepSeek服务
echo 5. 退出
echo.
set /p choice=请输入选择 (1/2/3/4/5): 

if "%choice%"=="1" goto COMMAND_MODE
if "%choice%"=="2" goto GUI_MODE
if "%choice%"=="3" goto DATA_ONLY
if "%choice%"=="4" goto DEEPSEEK_ONLY
if "%choice%"=="5" goto EXIT

echo 无效选择，请重新输入
timeout /t 2 /nobreak >nul
goto MAIN_MENU

:COMMAND_MODE
title 9F Power Plant - Command Line Mode
echo.
echo 启动命令行模式...
echo.

echo Step 1: Checking system environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found, please install Python first
    pause
    exit /b 1
)

echo Step 2: Checking network connection...
ping -n 1 59.51.82.42 >nul 2>&1
if errorlevel 1 (
    echo Warning: Cannot connect to SIS server, please check network
    echo System will continue to start, but real data collection will fail
    timeout /t 3 /nobreak >nul
)

echo Step 3: Starting Ollama service...
cd /d "%OLLAMA_DIR%"
if exist "start-ollama.bat" (
    echo Starting Ollama service...
    start "Ollama Service" cmd /c "start-ollama.bat"
) else (
    echo Warning: start-ollama.bat not found, assuming Ollama is installed
    echo If Ollama is not running, please start it manually
)

echo Waiting 20 seconds for Ollama service to fully start...
timeout /t 20 /nobreak >nul

echo Step 4: Starting DeepSeek model...
start "DeepSeek Model" cmd /k "cd /d "%OLLAMA_DIR%" && ollama run deepseek-r1:14b"

echo Waiting 45 seconds for DeepSeek model to load...
echo Note: DeepSeek R1:14b is a large model, loading may take time...
timeout /t 45 /nobreak >nul

echo Step 5: Verifying DeepSeek service status...
cd /d "%PROJECT_ROOT%"
python check_deepseek.py

echo Step 6: Starting main monitoring system...
cd /d "%PROJECT_ROOT%"
start "Main Monitoring System" cmd /k "conda activate limix && python main_system.py"

echo Waiting 10 seconds for main system to start and listen on ports...
timeout /t 10 /nobreak >nul

echo Step 7: Starting result receiver...
cd /d "%PROJECT_ROOT%"
start "Result Receiver" cmd /k "conda activate limix && python result_receiver.py"

echo Waiting 3 seconds for result receiver to start...
timeout /t 3 /nobreak >nul

echo Step 8: Starting fault receiver...
cd /d "%PROJECT_ROOT%"
start "Fault Receiver" cmd /k "conda activate limix && python fault_receiver.py"

echo Waiting 3 seconds for fault receiver to start...
timeout /t 3 /nobreak >nul

echo Step 9: Starting DeepSeek result receiver...
cd /d "%PROJECT_ROOT%"
start "DeepSeek Result Receiver" cmd /k "conda activate limix && python deepseek_receiver.py"

echo Waiting 3 seconds for DeepSeek result receiver to start...
timeout /t 3 /nobreak >nul

echo Step 10: Starting SIS data sender...
cd /d "%PROJECT_ROOT%"
start "Real SIS Data Sender" cmd /k "conda activate limix && python sis_data_sender.py"


echo.
echo =======================================================
echo           命令行模式启动完成!
echo =======================================================
echo.
echo 按任意键返回主菜单...
pause >nul
goto MAIN_MENU

:GUI_MODE
title 9F Power Plant - GUI Mode
echo.
echo 启动GUI图形界面...
echo.

echo Step 1: Checking system environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found, please install Python first
    pause
    exit /b 1
)

echo Step 2: Checking GUI dependencies...
python -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    echo Warning: PyQt5 not found, installing required dependencies...
    pip install PyQt5 matplotlib pyqtgraph
)

echo Step 3: Starting Ollama service...
cd /d "%OLLAMA_DIR%"
if exist "start-ollama.bat" (
    echo Starting Ollama service...
    start "Ollama Service" cmd /c "start-ollama.bat"
) else (
    echo Warning: start-ollama.bat not found, assuming Ollama is installed
    echo If Ollama is not running, please start it manually
)

echo Waiting 20 seconds for Ollama service to fully start...
timeout /t 20 /nobreak >nul

echo Step 4: Starting DeepSeek model...
start "DeepSeek Model" cmd /k "cd /d "%OLLAMA_DIR%" && ollama run deepseek-r1:14b"

echo Waiting 45 seconds for DeepSeek model to load...
echo Note: DeepSeek R1:14b is a large model, loading may take time...
timeout /t 45 /nobreak >nul

echo Step 5: Starting GUI application...
cd /d "%GUI_DIR%"
start "9F Power Plant GUI" cmd /k "conda activate limix && python gui_main.py"

echo.
echo =======================================================
echo           GUI图形界面启动完成!
echo =======================================================
echo.
echo 按任意键返回主菜单...
pause >nul
goto MAIN_MENU

:DATA_ONLY
title 9F Power Plant - Data Collection Only
echo.
echo 启动数据采集...
echo.

echo Step 1: Checking system environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found, please install Python first
    pause
    exit /b 1
)

echo Step 2: Starting SIS data sender...
cd /d "%PROJECT_ROOT%"
start "Real SIS Data Sender" cmd /k "conda activate limix && python sis_data_sender.py"

echo.
echo =======================================================
echo           数据采集模式启动完成!
echo =======================================================
echo.
echo 按任意键返回主菜单...
pause >nul
goto MAIN_MENU

:DEEPSEEK_ONLY
title 9F Power Plant - DeepSeek Only
echo.
echo 启动DeepSeek服务...
echo.

echo Step 1: Starting Ollama service...
cd /d "%OLLAMA_DIR%"
if exist "start-ollama.bat" (
    echo Starting Ollama service...
    start "Ollama Service" cmd /c "start-ollama.bat"
) else (
    echo Warning: start-ollama.bat not found, assuming Ollama is installed
    echo If Ollama is not running, please start it manually
)

echo Waiting 20 seconds for Ollama service to fully start...
timeout /t 20 /nobreak >nul

echo Step 2: Starting DeepSeek model...
start "DeepSeek Model" cmd /k "cd /d "%OLLAMA_DIR%" && ollama run deepseek-r1:14b"

echo.
echo =======================================================
echo           DeepSeek服务启动完成!
echo =======================================================
echo.
echo 按任意键返回主菜单...
pause >nul
goto MAIN_MENU

:EXIT
echo.
echo 感谢使用9F燃气电厂监控系统!
timeout /t 2 /nobreak >nul
exit