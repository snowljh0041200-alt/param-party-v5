@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== 바람 파티모집 v13 FINAL 업로드 =====
echo.
git add .
git commit -m "v13 final rebuild"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause
