@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v15.3 보스/파밍 통합 UI 수정 =====
echo 중요: data.json 파일은 절대 덮어쓰지 마세요.
echo.
git add .
git commit -m "v15.3 boss farm compact ui"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause
