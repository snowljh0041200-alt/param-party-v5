@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v33.0 notice realtime two column"
git push
pause
