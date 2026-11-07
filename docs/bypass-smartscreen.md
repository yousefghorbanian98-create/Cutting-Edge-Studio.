# عبور از هشدار SmartScreen (نسخهٔ بدون امضای دیجیتال)

تصمیم Owner (G14): این پروژه code-signing ندارد (هزینه + پیچیدگی). بنابراین ویندوز
در اولین اجرای نصب‌کننده هشدار «Windows protected your PC» نشان می‌دهد. این طبیعی است.

## مراحل
1. روی `CuttingEdgeV2-Setup-v1.0.0.exe` راست‌کلیک کنید → **Properties**
2. پایین تب **General** تیک **Unblock** را بزنید → **Apply** → **OK**
3. فایل را اجرا کنید. در پنجرهٔ آبی روی **More info** بزنید و سپس **Run anyway**.

## تأیید سالم بودن فایل قبل از اجرا
هر بار، SHA-256 را با فایل `.sha256` کنار آن مقایسه کنید:

```powershell
Get-FileHash .\CuttingEdgeV2-Setup-v1.0.0.exe -Algorithm SHA256
Get-Content .\CuttingEdgeV2-Setup-v1.0.0.exe.sha256
```

دو مقدار باید یکسان باشند. اگر نیستند، فایل را اجرا نکنید.

## آنتی‌ویروس
چون بستهٔ نصب شامل `python-embed`، باینری PyInstaller و مدل‌های ONNX است، برخی
آنتی‌ویروس‌ها false positive می‌دهند. پوشهٔ نصب را استثنا کنید:
```
C:\Program Files\CuttingEdgeV2\
```
و در صورت نیاز پوشهٔ داده:
```
%APPDATA%\CuttingEdgeV2\
```
