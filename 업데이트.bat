@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v16.0 일정/실시간채팅 대시보드 =====
echo 중요: data.json 파일은 절대 덮어쓰지 마세요.
echo.
git add .
git commit -m "v16.0 schedule chat dashboard"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause
