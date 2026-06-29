@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v24.0 login ajax chat"
git push
pause
