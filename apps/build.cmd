set v=1.5.0

cd YACPgen
echo VERSION="%v%" > version.py
pyinstaller -y YACPgen.spec
cd ..

cd YACPcal
echo VERSION="%v%" > version.py
pyinstaller -y YACPcal.spec
cd ..


iscc "/dMyAppVersion=%v%" YACP.iss

REM copy YACPgen/dist/YACPgen.exe binaries/YACPgen-x86_64-%v%.exe
REM copy YACPcal/dist/YACPcal.exe binaries/YACPcal-x86_64-%v%.exe

pause
