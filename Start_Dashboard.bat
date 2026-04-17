@echo off
cd /d %~dp0..
title Autonomous Intelligence Systems  Project Dashboard
color 0B
echo Starting your secure Agent Dashboard...
echo Ensuring virtual environment...

if not exist ".venv\Scripts\python.exe" (
    echo Error: Could not find Python virtual environment.
    pause
    exit /b
)

echo Routing dashboard to background...
cscript //nologo run_hidden.vbs

echo Done! The dashboard is now running invisibly in the background.
echo Opening dashboard in your browser...
timeout /t 2 >nul
start http://localhost:8080
