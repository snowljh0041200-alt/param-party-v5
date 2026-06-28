@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v12 파밍 문파전용 업데이트 =====
echo.
git add .
git commit -m "v12 private farming board"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause
