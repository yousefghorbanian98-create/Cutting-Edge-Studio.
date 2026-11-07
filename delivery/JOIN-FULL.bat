@echo off
echo Joining Cutting Edge FULL package (like game repack)...
copy /b CuttingEdge-Studio-v1.0.0-FULL.zip.part00 + CuttingEdge-Studio-v1.0.0-FULL.zip.part01 CuttingEdge-Studio-v1.0.0-FULL.zip
echo Verifying...
certutil -hashfile CuttingEdge-Studio-v1.0.0-FULL.zip SHA256
echo Done! Now extract FULL.zip -> Setup.exe inside
pause
