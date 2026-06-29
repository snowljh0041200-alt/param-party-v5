@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v26.19 force edit member panel"
git push
pause
