@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v40.3 realtime board version refresh"
git push
pause
