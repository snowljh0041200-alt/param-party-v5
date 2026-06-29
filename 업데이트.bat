@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v28.0 final toast fix"
git push
pause
