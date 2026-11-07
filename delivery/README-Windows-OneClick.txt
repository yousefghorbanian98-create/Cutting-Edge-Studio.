Cutting Edge Studio v1.0.0 — Windows Game-like Installer (One-Click)
====================================================================
1. دانلود هر دو Part را در یک پوشه بگذارید:
   - CuttingEdge-Studio-v1.0.0-Windows-Part1.zip
   - CuttingEdge-Studio-v1.0.0-Windows-Part2.zip
2. هر دو را Extract کنید (Extract Here) — کنار هم یک فولدر می‌سازند:
   CuttingEdgeStudio-v1.0.0-Windows/
   ├── Setup.bat  ← فقط این را به عنوان Administrator اجرا کنید
   ├── Setup.ps1
   ├── OneClick-Setup.ps1  (گراف 6 مرحله‌ای)
   ├── Data1/ (Core 1.1GB)
   └── Data2/ (Docs + Licenses + Models placeholder)
3. Setup قبل شروع:
   - 8 پیش‌نیاز را تست می‌کند (Node 22, Python 3.11, Rust, Git, FFmpeg, WebView2, VC++ Redist)
   - کمبودها را با winget خودش نصب می‌کند
   - محل نصب را می‌پرسد، فضای دیسک را چک می‌کند (Light 1.2GB / Full 5GB)
   - همه مراحل را با گراف جهانی نشان می‌دهد و هر مرحله را راستی‌آزمایی می‌کند
4. لاگ: %TEMP%\CuttingEdge-Setup-*.log

نیاز: Windows 11 x64, Run as Administrator
