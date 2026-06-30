@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v40.9 boss endtime voice hardfix"
git push
pause
