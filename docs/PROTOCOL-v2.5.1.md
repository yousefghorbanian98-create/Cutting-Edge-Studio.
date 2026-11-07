# Cutting Edge v2 — Protocol v2.5.1 (DELTA)

این فایل فقط **دلتای** تصمیم‌های اصلاحی نسبت به `PROTOCOL-ISSUES.md` (بخش RESOLUTION LOG) را
به‌صورت قابل استناد نگه می‌دارد. هر LOCK/بندی که اینجا نیامده، مطابق v2.5 FINAL معتبر است.

## LOCKهای اصلاح‌شده
- **LOCK-04 (v2.5.1):** تشخیص آبجکت = **YOLOX** (کد Apache-2.0، وزن MIT، ~35MB، وزن از GitHub Releases،
  بدون دانلود خودکار). Fallback مجاز: RT-DETR (PaddleDetection، Apache-2.0).
  YOLO-NAS و YOLOv8 هر دو ممنوع (اولی وزن غیرتجاری، دومی AGPL).
- **LOCK-07 (v2.5.1):** Builder روی شاخهٔ `arena/dbb53bc2-cutting-edge-studio` کار می‌کند؛
  هر فاز یک PR به `main`؛ merge با Owner.
- **LOCK-12 (v2.5.1):** رفرنس‌ها و موزیک **باندل نمی‌شوند**. اپ پوشه‌های
  `%APPDATA%/CuttingEdgeV2/{references,music,b-roll,voice-overs}` را می‌سازد و کاربر import می‌کند.
- **LOCK-19:** بدون تغییر — توقف و تأیید بعد از هر فاز اجباری است.

## تغییرات استک
| قبلی | جدید | دلیل |
|---|---|---|
| YOLO-NAS (super-gradients) | YOLOX | وزن غیرتجاری + پروژهٔ رهاشده |
| madmom | librosa + scipy.signal (fallback: Beat-This) | بدون wheel cp311 + مدل NC |
| onnxruntime-gpu | onnxruntime (CPU) + GPU اختیاری | حجم/لایسنس CUDA |
| 20 رفرنس باندل‌شده | user-import | کپی‌رایت |
| 350MB موزیک باندل‌شده | user-import (CC0/CC-BY) | کپی‌رایت |
| PDF docs | Markdown | بدون pandoc/weasyprint |
| installer ~3.0GB | **~3.5GB** | +WebView2 fixed-version |

## Whitelist v2.5.1
```
MIT, BSD 2/3/0, Apache 2.0, ISC, zlib, MPL 2.0, LGPL (dynamic only),
Unicode, Unlicense, CC0, PSF, OFL 1.1, Boost, PyInstaller-Bootloader-Exception
```
## Blacklist v2.5.1 (بدون تغییر)
```
GPL (standalone), AGPL, CC-BY-NC, CC-BY-SA (code), SSPL, BUSL,
Proprietary, Non-commercial weights
```

## Golden Set و متریک پذیرش P6 (G12)
| # | متریک | روش | آستانهٔ قبولی |
|---|-------|-----|----------------|
| 1 | Cut Length Distribution | KS-test خروجی vs رفرنس | p > 0.05 |
| 2 | Shot Type Accuracy | F1، CLIP zero-shot vs ground truth | گزارش‌شده |
| 3 | Beat Alignment | میانگین فاصلهٔ کات از نزدیک‌ترین beat | < 100ms |
| 4 | Pacing Similarity | همبستگی Pearson انرژی زمانی | r > 0.7 |
| 5 | Color Match | ΔE میانگین هیستوگرام | < 10 |

قبولی نهایی P6 = برآورده شدن **۳ از ۵** متریک روی Golden Set.
