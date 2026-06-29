@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v31.3 recover card slot fit"
git push
pause
