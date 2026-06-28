@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v13.7 파밍 지분방식 정산 업데이트 =====
echo.
git add .
git commit -m "v13.7 farming share weight settlement"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause
