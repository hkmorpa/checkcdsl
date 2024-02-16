@echo off
setlocal enabledelayedexpansion

del "C:\checkcdsl\status.txt"

:loop

python "C:\checkcdsl\cdsl_pledge_approval.py"

rem Count the number of lines in pan_email.txt
set "pan_email_count=0"
for /f %%i in ('type "C:\checkcdsl\pan_email.txt" ^| find /c /v ""') do set "pan_email_count=%%i"

rem Count the number of lines in status.txt
set "status_count=0"
for /f %%i in ('type "C:\checkcdsl\status.txt" ^| find /c /v ""') do set "status_count=%%i"

rem Check if the count in pan_email.txt is less than the count in status.txt
if !status_count! lss !pan_email_count! (
    rem Run the Python script
    python "C:\checkcdsl\cdsl_pledge_approval.py"
    goto :loop
)

endlocal
