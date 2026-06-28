@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v18.3 관리자 500 핫픽스 =====
git add .
git commit -m "v18.3 admin 500 hotfix"
git push
pause
