@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v17.4 날짜/시간 최종 수정 =====
git add .
git commit -m "v17.4 date time final fix"
git push
pause
