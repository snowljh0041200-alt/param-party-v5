@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v23.1 approval duplicate slim buttons"
git push
pause
