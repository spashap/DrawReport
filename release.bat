@echo off
REM One-command release: bump version -> commit -> push.
REM Usage:  release.bat "commit message"   (message optional)
setlocal
cd /d %~dp0

set "MSG=%~1"
if "%MSG%"=="" set "MSG=site updates"

echo == 1/4 bump version ==
venv\Scripts\python.exe scripts\bump_version.py || goto :err

echo == 2/4 git add ==
git add -A || goto :err

echo == 3/4 git commit ==
for /f "usebackq delims=" %%v in (`type VERSION`) do set "VER=%%v"
git commit -m "%MSG% (V%VER%)" || goto :err

echo == 4/4 git push ==
git push || goto :err

echo.
echo == DONE -> pushed V%VER% ==
goto :eof

:err
echo.
echo ERROR - stopped. Nothing pushed past the failed step.
exit /b 1
