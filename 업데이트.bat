@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== 바클 파티모집 v8 ADMIN 업데이트 =====
echo.
git add .
git commit -m "v8 admin final"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause
