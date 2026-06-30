@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v41.1 create force main fix"
git push
pause
