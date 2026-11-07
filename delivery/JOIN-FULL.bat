@echo off
echo Joining FULL parts...
copy /b CuttingEdge-Studio-v1.0.0-FULL.zip.part00+CuttingEdge-Studio-v1.0.0-FULL.zip.part01 CuttingEdge-Studio-v1.0.0-FULL.zip
echo Done — verify with: certutil -hashfile CuttingEdge-Studio-v1.0.0-FULL.zip SHA256
