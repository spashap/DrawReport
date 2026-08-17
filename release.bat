@echo off
REM One-command release: bump version -> commit -> push -> deploy to the server.
REM
REM Usage:  release.bat "commit message"        full release (push AND deploy)
REM         release.bat "message" --no-deploy   push only, leave the server alone
REM         release.bat --deploy-only           deploy what is already on GitHub
REM
REM The server step needs SSH key auth to root@5.78.181.152. If it ever asks for a
REM password, run drawreportDeploy\0-setup-ssh-key.bat once.
REM
REM Order matters: nothing is pushed if the commit fails, and nothing is deployed if the
REM push fails - so the server can never end up ahead of GitHub.
REM
REM NOTE ON STYLE: this script is deliberately written as linear steps with GOTO rather
REM than IF ( ... ) blocks. Inside a parenthesised block cmd.exe expands %VAR% when the
REM block is PARSED, not when it runs, so a variable set inside the block reads back empty
REM - which silently produced commit messages like "(V)" with no version in them.
setlocal
cd /d %~dp0

set "SERVER=root@5.78.181.152"
set "APPDIR=/var/www/DrawReport"
set "SITE=https://drawreport.com"

set "MSG=%~1"
set "FLAG=%~2"
set "DEPLOY=1"

if /i "%MSG%"=="--deploy-only" goto :deploy_only
if "%MSG%"=="" set "MSG=site updates"
if /i "%FLAG%"=="--no-deploy" set "DEPLOY=0"

echo == 1/5 bump version ==
venv\Scripts\python.exe scripts\bump_version.py || goto :err
for /f "usebackq delims=" %%v in (`type VERSION`) do set "VER=%%v"

echo == 2/5 git add ==
git add -A || goto :err

echo == 3/5 git commit ==
git commit -m "%MSG% (V%VER%)" || goto :err

echo == 4/5 git push ==
git push || goto :err
echo    pushed V%VER%

if "%DEPLOY%"=="0" goto :pushed_only
goto :deploy

:deploy_only
for /f "usebackq delims=" %%v in (`type VERSION`) do set "VER=%%v"
echo == deploy-only: skipping bump/commit/push ==

:deploy
echo == 5/5 deploy on the server ==
REM deploy.sh lives in the repo, so the `git pull` inside it updates the deploy logic too.
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new %SERVER% "bash %APPDIR%/deploy.sh" || goto :deployerr

echo.
echo == health check ==
REM Follows redirects (-L) so the locale redirect on "/" is not a false alarm, and ASSERTS
REM 200 on each page - a check that only prints status codes would report a green deploy
REM while the site returned 500. A colon rather than an arrow because a literal '>' here
REM would need a cmd escape that then travels to the remote shell and prints as output.
ssh -o BatchMode=yes %SERVER% "bad=0; for u in / /free/ /en/report; do c=$(curl -sSL -o /dev/null -w '%%{http_code}' %SITE%$u); printf '  %%-14s %%s\n' \"$u\" \"$c\"; [ \"$c\" = 200 ] || bad=1; done; exit $bad" || goto :healtherr

echo.
echo == DONE -^> V%VER% pushed and deployed ==
goto :eof

:pushed_only
echo.
echo == DONE -^> pushed V%VER%. Server NOT touched (--no-deploy). ==
echo    Deploy it later with:  release.bat --deploy-only
goto :eof

:err
echo.
echo ERROR - stopped before pushing. Nothing reached GitHub or the server.
exit /b 1

:deployerr
echo.
echo ERROR - the push SUCCEEDED but the server deploy FAILED.
echo GitHub has V%VER%; the server does not.
echo Nothing is half-applied: deploy.sh restarts services only after the pull and the
echo dependency install succeed, and it prints the journal of any unit that did not
echo come back up.
echo.
echo Retry just the server step with:   release.bat --deploy-only
exit /b 1

:healtherr
echo.
echo WARNING - deployed, but the health check could not reach the site.
echo Check nginx and the units:  ssh %SERVER% "systemctl status drawreport-web"
exit /b 1
