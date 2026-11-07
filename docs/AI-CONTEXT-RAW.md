# AI-CONTEXT-RAW — Cutting Edge Studio v1.0.0
# این فایل برای کپی مستقیم به ChatGPT/Claude/Gemini است - یک فایل = کل پروژه
# Last: 2026-11-07 | Commit: 9bed4e1 | Branch: arena/184ede4b-cutting-edge-studio | Release: v1.0.0

## پروژه چیست؟ (یک پاراگراف برای AI)
Cutting Edge Studio v1.0.0 یک ویرایشگر ویدیوی ورزشی آفلاین برای ویندوز است که هسته آن **Style Match** است: استاد ۱۰ کلیپ خودش + ۱ ویدیوی رفرنس (مثلاً بدنسازی حرفه‌ای) را می‌دهد، سیستم DNA تدوین رفرنس (ریتم کات، ترکیب شات، زبان دوربین، رنگ، گرید ضرب) را استخراج کرده و به صورت خودکار روی کلیپ‌های استاد اعمال می‌کند — با پیش‌نمایش یک‌کلیک و خروجی نهایی یک‌کلیک. کاملاً آفلاین، بدون تله‌متری/CDN، لایسنس MIT/OFL/LGPL.

## استک فنی (برای AI)
- **Backend:** FastAPI (Python 3.11) — sidecar روی 127.0.0.1:8756، SQLite، 333 تست، پوشش 93%، ruff ALL clean
- **Frontend:** React 18 + Vite 7 + TypeScript 5 + Tailwind 3 — 168 تست، ESLint 0، بیلد 1.8M (40+ فونت Vazirmatn/Inter/JetBrains Mono OFL-1.1)
- **Desktop:** Tauri v2 (Rust) — CSP سخت، sidecar spawn، WebView2، NSIS فارسی/انگلیسی
- **Media:** FFmpeg LGPL shared (نه GPL libx264)، NVENC → openh264 fallback، JobRegistry با progress/cancel
- **AI Models:** MediaPipe Pose > CLIP > YOLOX > Faster-Whisper > Piper TTS > TransNetV2 — همه پین‌شده با SHA256 در scripts/pins.json (6 مدل فعلاً null صادقانه)
- **امنیت:** zizmor 0 findings، gitleaks 8.30.1 PASS، Trivy HIGH/CRITICAL PASS، 21 اکشن پین به SHA

## ۱۸ دروازه ریکاوری — وضعیت برای AI
| ID | عنوان | وضعیت | عدد |
|---|---|---|---|
| R1 | ایمپورت واقعی + پخش منبع | ✅ LOCAL PASS | 18/18 browser |
| R1b | بازگشایی پس از ری‌استارت | ✅ LOCAL PASS | 26/26 + restart |
| R2a | جاب دیکود واقعی (hash/probe/cancel) | ✅ LOCAL PASS | 26/26 + SIGKILL |
| R2b1 | آداپتور ریتم librosa | ✅ ADAPTER PASS | 3/3 fixtures |
| R2b2 | جاب صوتی ایزوله | ✅ LOCAL PASS | 23/23 browser |
| R2b3 | کاندید شات scdet | ✅ LOCAL PASS | 25/25 browser |
| R2b4 | ریکاوری scratch محافظه‌کارانه | ✅ LOCAL PASS | 54/54 browser |
| R2c | دسکتاپ same-origin | ✅ VERIFIED 4d4a639 | frozen 27/27 + installed 20/20 + WebView 11/11 |
| A1 | انسجام معماری | ✅ | Madge 0 حلقه + 3 قانون DC |
| R2 | ارکستراسیون تحلیل | ✅ VERIFIED 5b45ff0 | 503 بدون دانلود پنهان |
| R3 | پیش‌نمایش/خروجی | ✅ VERIFIED 5b45ff0 | EDL→FFmpeg, JobRegistry 99% |
| R3-hard | پوشش orchestrator | ✅ 99% | 158 stmts 0 miss |
| C1 | قرارداد بنچمارک | ✅ VERIFIED 01c2761 | CapCut/Filmora |
| R4 | بسته‌بندی دسکتاپ | ✅ VERIFIED 7f0fe2f | Tauri NSIS, pins LGPL |
| C3 | اولویت شکاف | ✅ PROVISIONAL | Must/Should OSS |
| R5 | تمایز | ✅ VERIFIED e5d0615 | Persian RTL, hypothesis |
| R6 | پذیرش انتشار سبک | ✅ VERIFIED 893ab49 | VERSION 1.0.0 |
| C2 | مشاهده رقبا | ⏸️ BLOCKED | نیاز نصب دستی |

260/260 مرحله نویسش تاریخی است، پذیرش محصول BLOCKED صادقانه برای Full 3.5GB.

## ساختار پکیج — برای AI
```
Cutting-Edge-Studio./
├── backend/app/        # API, services, schemas (93%)
├── frontend/src/       # React + 20 test files
├── frontend/dist/      # بیلد 1.8M (در tar.gz)
├── src-tauri/          # Tauri conf v1.0.0
├── scripts/build-installer.ps1 + pins.json (FFmpeg e907b01f... LGPL)
├── delivery/
│   ├── CuttingEdge-Studio-v1.0.0-light.tar.gz (8.9M)
│   ├── CuttingEdge-Studio-v1.0.0-Windows.zip (8.7M) ← Game-like: Data1+Data2 ZIP -9
│   └── verification-logs-v1.0.0.tar.gz (11K)
├── docs/FINAL-DELIVERY-v1.0.0.md ← مرجع تحویل (230 خط)
└── licenses/THIRD-PARTY.md
```

## نصب ویندوز — برای AI
**Light (همین پکیج، بدون مدل حجیم):**
```powershell
Expand-Archive CuttingEdge-Studio-v1.0.0-Windows.zip C:\CuttingEdge-Setup
pwsh -File scripts/build-installer.ps1 -WithoutPinnedBinaries
# خروجی: delivery/CuttingEdgeV2-Setup-v1.0.0.exe → Run as Admin
```
**Full (3.5GB آفلاین):**
```powershell
pwsh -File scripts/build-installer.ps1 -UpdatePins # بازبینی هش
pwsh -File scripts/build-installer.ps1            # full + .sha256
```

## تایید — برای AI
```bash
cd backend && PYTHONPATH=. pytest --cov=app -q # 333 passed, 6 skipped
cd frontend && npm run lint && npx vitest run   # 168 passed, 20 files
python -m mypy app # Success 72 files
zizmor . # No findings (7 suppressed)
```

## لینک‌ها — برای AI
- Repo: https://github.com/yousefghorbanian98-create/Cutting-Edge-Studio.
- Release v1.0.0: https://github.com/yousefghorbanian98-create/Cutting-Edge-Studio./releases/tag/v1.0.0
- RAW این فایل: https://github.com/yousefghorbanian98-create/Cutting-Edge-Studio./blob/arena/184ede4b-cutting-edge-studio/docs/AI-CONTEXT-RAW.md
- Windows.zip RAW: https://github.com/yousefghorbanian98-create/Cutting-Edge-Studio./blob/arena/184ede4b-cutting-edge-studio/delivery/CuttingEdge-Studio-v1.0.0-Windows.zip?raw=true
- FINAL-DELIVERY RAW: https://github.com/yousefghorbanian98-create/Cutting-Edge-Studio./blob/arena/184ede4b-cutting-edge-studio/docs/FINAL-DELIVERY-v1.0.0.md
- Checklist BLOCKED صادقانه: docs/RELEASE-CHECKLIST.md, docs/R6-RELEASE-LIGHT.md

## دستور به AI استاد
"تو یک داور پروژه دانشجویی هستی. با توجه به AI-CONTEXT-RAW بالا، در 30 ثانیه بگو: پروژه چیست، چه چیزی کامل است، چه چیزی صادقانه BLOCKED است، و کیفیت کد چطور است. بدون ادعای کاذب."

## کلیدواژه برای AI
Cutting Edge Studio, Style Match, Tauri, FastAPI, FFmpeg LGPL, MediaPipe, CLIP, YOLOX, NVENC, openh264, zizmor, Protocol v2.5.1, 260/260, 93% coverage, Light Delivery
