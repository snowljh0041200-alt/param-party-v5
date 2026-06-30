@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v40.7 boss time voice fix"
git push
pause
