#!/bin/bash
# Join on Linux/macOS
cat CuttingEdge-Studio-v1.0.0-FULL.zip.part* > CuttingEdge-Studio-v1.0.0-FULL.zip
sha256sum -c CuttingEdge-Studio-v1.0.0-FULL.zip.sha256
unzip -l CuttingEdge-Studio-v1.0.0-FULL.zip | head -20
