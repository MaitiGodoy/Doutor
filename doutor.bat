@echo off
setlocal
set DOUTOR_ROOT=%~dp0
python "%DOUTOR_ROOT%main.py" %*
endlocal
