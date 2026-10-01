@echo off
REM Weekly scrape of imot.bg Sofia apartments. Scheduled via Windows Task Scheduler.
cd /d "%~dp0"
python -m imoti.pipeline
