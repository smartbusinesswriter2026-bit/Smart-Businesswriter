@echo off
rem One enrichment pass: turn what paper runs searched for into corpus material.
rem
rem   enrich_cycle.bat          collect + score + research + fetch + index
rem   enrich_cycle.bat fast     collect + score only (no downloads, no index)
rem
rem The full pass is the nightly job.  It never invents a source: a work enters
rem only because a real search needed it, and a full text enters only when its
rem licence is open or the owner approves it in the admin UI.
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if not defined BP_CORPUS_DB set "BP_CORPUS_DB=%~dp0..\..\corpus-state\corpus.sqlite"
if not defined CORPUS_MEILI_URL set "CORPUS_MEILI_URL=http://127.0.0.1:7700"
if not defined CORPUS_INDEX set "CORPUS_INDEX=pages"
set "LOG=%~dp0..\..\corpus-state\enrich.log"

echo [%DATE% %TIME%] enrichment start arg=%~1 db=%BP_CORPUS_DB%>> "%LOG%"
if /i "%~1"=="fast" (
  python "%~dp0enrich.py" collect >> "%LOG%" 2>&1
  python "%~dp0enrich.py" score >> "%LOG%" 2>&1
) else (
  python "%~dp0enrich.py" run >> "%LOG%" 2>&1
)
set "CODE=!ERRORLEVEL!"
echo [%DATE% %TIME%] enrichment end exit=!CODE!>> "%LOG%"

if not "!CODE!"=="0" (
  echo The enrichment pass failed; see %LOG%
  exit /b !CODE!
)
echo Enrichment pass finished; see %LOG%
endlocal
