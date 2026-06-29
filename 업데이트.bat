@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v21.5 live ready online users"
git push
pause
