@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== v16.2 통합채팅 메인 표시 핫픽스 =====
echo 중요: data.json 파일은 절대 덮어쓰지 마세요.
echo.
git add .
git commit -m "v16.2 chat html hotfix"
git push
echo.
echo ===== 완료. Render 자동배포를 기다리세요. =====
pause
