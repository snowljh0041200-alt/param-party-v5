@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v15.4 UI 재배치 / 보스 자동정렬 =====
echo 중요: data.json 파일은 절대 덮어쓰지 마세요.
echo.
git add .
git commit -m "v15.4 ui layout boss sort"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause
