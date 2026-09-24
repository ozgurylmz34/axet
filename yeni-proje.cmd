@echo off
rem yeni-proje.cmd - sorarak aXet SAP projesi kurar. Tek kod yolu: scripts\yeni_proje.py (%%yeni-proje skill'i de bunu cagirir).
rem Kullanim: yeni-proje.cmd            (sorular terminalde tek tek sorulur)
rem           yeni-proje.cmd --help     (bayrakli kullanim)
setlocal
python --version >nul 2>nul
if errorlevel 1 goto python_yok
rem Z80 nit: eski Python 'bulunamadi' degil 'surum yetersiz' der ve erken durur (esik: install.PY_ASGARI, parite testi).
python -c "import sys;sys.exit(0 if sys.version_info>=(3,12) else 1)" >nul 2>nul
if errorlevel 1 goto python_eski
python "%~dp0scripts\yeni_proje.py" %*
exit /b %errorlevel%

:python_eski
echo HATA: python bulundu ama surumu yetersiz - Python 3.12+ gerekli. Kurulu surum:
python --version
echo Guncelleme: sirketinin yazilim merkezinden (Software Center / Company Portal) kur ya da BT'den iste;
echo resmi indirme: https://www.python.org/downloads/windows/  - sonra YENI bir terminal ac ve tekrar calistir.
exit /b 9009

:python_yok
echo HATA: python bulunamadi ya da calismiyor - PATH'te Python 3.12+ gerekli.
echo Kurulum: sirketinin yazilim merkezinden (Software Center / Company Portal) kur ya da BT'den iste;
echo resmi indirme: https://www.python.org/downloads/windows/  - sonra YENI bir terminal ac ve tekrar calistir.
echo Not: Windows'un "python" magaza kisayolu gercek Python degildir.
exit /b 9009
