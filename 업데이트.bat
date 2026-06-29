@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v31.0 four grid realtime panel"
git push
pause
