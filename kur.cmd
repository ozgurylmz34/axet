@echo off
rem aXet template kurulumu: kur.ps1'i bu klasorden calistirir (parametreler aynen gecer: -Hedef -Kaynak -Kaldir -DenemeModu).
rem -ExecutionPolicy Bypass: internetten indirilmis (Zone.Identifier) betik RemoteSigned politikasinda aksi halde engellenir.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kur.ps1" %*
exit /b %ERRORLEVEL%
