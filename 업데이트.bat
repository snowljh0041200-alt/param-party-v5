@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v36.7 online admin only"
git push
pause
