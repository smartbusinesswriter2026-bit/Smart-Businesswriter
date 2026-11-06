@echo off
rem Seed the corpus from every framework and theory the pipeline can name.
rem
rem   seed_frameworks.bat --dry-run
rem   seed_frameworks.bat
rem   seed_frameworks.bat --frameworks "Porter,Ansoff,PESTEL,SWOT,VRIO" --fetch 20
rem
rem This is a one-time (or occasional) discovery pass.  The nightly
rem enrich_cycle.bat handles the demand the papers create afterwards.
setlocal
cd /d "%~dp0"

if not defined BP_CORPUS_DB set "BP_CORPUS_DB=%~dp0..\..\corpus-state\corpus.sqlite"
if not defined CORPUS_MEILI_URL set "CORPUS_MEILI_URL=http://127.0.0.1:7700"
if not defined CORPUS_INDEX set "CORPUS_INDEX=pages"

python "%~dp0seed_frameworks.py" %*
endlocal
