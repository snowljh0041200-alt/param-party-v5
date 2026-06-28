@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v15.1 오픈 준비 기능 업데이트 =====
echo 중요: data.json 파일은 절대 덮어쓰지 마세요.
echo.
git add .
git commit -m "v15.1 open ready features"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause
