@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v26.5 autoclose copy format"
git push
pause
