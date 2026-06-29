@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v22.8 admin delete premium tabs"
git push
pause
