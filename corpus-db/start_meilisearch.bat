@echo off
cd /d "%~dp0"
start "Meilisearch" /min meilisearch.exe
echo Meilisearch starting on http://127.0.0.1:7700
pause