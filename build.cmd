@echo off
REM #############################################################################################
REM                      Build package script. multi and single file modes.
REM          For more information about this script, read PyInstaller documentation.
REM #############################################################################################
py -m PyInstaller -c -i assets\icon.ico --add-data assets;assets --noconfirm --noconsole lol-automation.pyw
py -m PyInstaller -c -F -i assets\icon.ico --add-data assets;assets --noconfirm --noconsole lol-automation.pyw
pause
pause