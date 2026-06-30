@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v40.4 hunt places online compact"
git push
pause
