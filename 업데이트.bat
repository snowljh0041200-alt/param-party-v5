@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v22.9 admin post list premium buttons"
git push
pause
