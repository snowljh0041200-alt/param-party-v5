@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v16.5 파밍 안정화/시간 최종 수정 =====
echo 중요: data.json 파일은 절대 덮어쓰지 마세요.
echo.
git add .
git commit -m "v16.5 farming stable time fix"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause
