Cutting Edge Studio v1.0.0 — FULL Package (GitHub Split Demo)
=============================================================
این فولدر نماینده پکیج کامل 3.5GB است که روی لینوکس نمی‌شود 3.5GB واقعی ساخت.
برای دمو، همین 3 فایل 18MB را به عنوان FULL در نظر گرفتیم و با سقف 9MB به 2 تکه تقسیم می‌کنیم.
در ویندوز واقعی: 3.5GB → 2 تکه 1750MB (سقف GitHub 2GB)

محتوا:
- CuttingEdge-Studio-v1.0.0-Windows.zip (8.7M) — Data1+Data2 GamePack
- CuttingEdge-Studio-v1.0.0-light.tar.gz (8.9M) — سورس + فرانت بیلد
- verification-logs-v1.0.0.tar.gz (11K)

بازسازی FULL واقعی روی ویندوز:
  pwsh -File scripts/build-installer.ps1              # → 3.5GB exe
  pwsh -File scripts/split-for-github.ps1 -File delivery/CuttingEdgeV2-Setup-v1.0.0.exe
  # → 2 تکه 1750MB آماده آپلود
