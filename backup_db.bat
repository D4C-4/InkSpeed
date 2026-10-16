@echo off
setlocal
python "%~dp0backup_db.py"
if errorlevel 1 exit /b 1
