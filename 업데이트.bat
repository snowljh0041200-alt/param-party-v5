@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v13.4 파밍 선집합/후집합 정산 업데이트 =====
echo.
git add .
git commit -m "v13.4 farming groups settlement"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause
