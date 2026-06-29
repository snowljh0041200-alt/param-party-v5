@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add .
git commit -m "v40.0 mmorpg ui remaster"
git push
pause
