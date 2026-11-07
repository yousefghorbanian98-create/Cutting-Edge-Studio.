#!/bin/bash
cat CuttingEdge-Studio-v1.0.0-FULL.zip.part00 CuttingEdge-Studio-v1.0.0-FULL.zip.part01 > CuttingEdge-Studio-v1.0.0-FULL.zip
sha256sum -c CuttingEdge-Studio-v1.0.0-FULL.zip.sha256
