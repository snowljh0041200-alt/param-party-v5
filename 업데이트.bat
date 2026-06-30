@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v41.0 boss endtime server fix"
git push
pause
