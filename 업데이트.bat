@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v25.4 pending direct fix"
git push
pause
