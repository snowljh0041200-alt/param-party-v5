@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v39.1 fantasy luxury theme"
git push
pause
