@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== 월하 연가 연희 파티모집 v11 FINAL 업로드 =====
echo.
git add .
git commit -m "v11 final clean rebuild"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause
