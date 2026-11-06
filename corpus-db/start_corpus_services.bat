@echo off
rem Start the two local services the corpus needs before a paper run:
rem
rem   Meilisearch        http://127.0.0.1:7700   (the search index)
rem   corpus service     http://127.0.0.1:7710   (the learning log + owner admin)
rem
rem Both are started only when they are not already answering, so running this
rem twice is safe.  The pipeline reads the corpus through Meilisearch and writes
rem its learning log through the admin service; neither may hold a paper hostage.
setlocal
cd /d "%~dp0"

if not defined BP_CORPUS_DB set "BP_CORPUS_DB=%~dp0..\corpus-state\corpus.sqlite"
if not defined CORPUS_MEILI_URL set "CORPUS_MEILI_URL=http://127.0.0.1:7700"
if not defined CORPUS_INDEX set "CORPUS_INDEX=pages"

powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:7700/health; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
if errorlevel 1 (
  echo Starting Meilisearch on http://127.0.0.1:7700
  start "Meilisearch" /min "%~dp0meilisearch.exe"
  timeout /t 3 /nobreak >nul
) else (
  echo Meilisearch is already answering on http://127.0.0.1:7700
)

powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:7710/api/corpus/stats; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
if errorlevel 1 (
  echo Starting the corpus service on http://127.0.0.1:7710
  start "Corpus service" /min python "%~dp0build\corpus_service.py" --port 7710
  timeout /t 2 /nobreak >nul
) else (
  echo The corpus service is already answering on http://127.0.0.1:7710
)

echo.
echo Meilisearch:    http://127.0.0.1:7700
echo Corpus service: http://127.0.0.1:7710
echo Admin page:     http://127.0.0.1:7710/
echo.
echo The canonical database is %BP_CORPUS_DB%
endlocal
