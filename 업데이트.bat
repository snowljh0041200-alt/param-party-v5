@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v31.7 inline layout hard fix"
git push
pause
