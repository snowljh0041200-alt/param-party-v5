@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v6 stable online users"
git push
pause
