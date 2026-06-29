@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v26.25 direct toast fix"
git push
pause
