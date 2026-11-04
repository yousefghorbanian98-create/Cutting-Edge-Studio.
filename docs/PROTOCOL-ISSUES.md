# Cutting Edge v2 — Protocol v2.5: تناقض‌ها، ریسک‌ها و ابهام‌ها

وضعیت: منتظر تصمیم Owner — هیچ کدی commit/push نمی‌شود تا این لیست تعیین تکلیف شود.
منبع: Protocol v2.5 FINAL + بررسی مستقیم محیط اجرا + بررسی لایسنس پکیج‌ها (PyPI / منابع رسمی)

---

## A. تناقض‌های داخلی خود پروتکل

A1. §13 «فقط ۵ نوع پیام» و «گزارش پیشرفت ممنوع» ←→ §18 (Weekly Evidence Report) و §19 (گزارش هر فاز).
    ⇒ گزارش Evidence به‌عنوان پیام مجاز نوع ۱ (Final Delivery / Phase Delivery) تعریف شود.

A2. LOCK-19 (توقف و تأیید بعد از هر فاز) ←→ انتخاب شما «all_source: بدون توقف تا P8».
    ⇒ یکی باید اصل شود؛ هر دو با هم قابل اجرا نیست.

A3. LOCK-05 «کاملاً آفلاین» ←→ §5 (tauri-plugin-updater) + §12 (delta updates) و §12 «CDN ممنوع».
    هیچ سرور/URL به‌روزرسانی تعریف نشده. آپدیت دلتا بدون سرور ممکن نیست.
    ⇒ منبع آپدیت = GitHub Releases، فقط با کلیک صریح کاربر، بدون بررسی خودکار.

A4. §4 شرط Auto-Fail #5 «دانلود در runtime ممنوع» ←→ کتابخانه‌هایی که خودشان وزن دانلود می‌کنند:
    super-gradients (CDN دِسی)، faster-whisper (Hugging Face)، piper voices، open_clip، mediapipe (.task).
    ⇒ همهٔ آداپترها فقط مسیر محلی بگیرند؛ دانلود خودکار کتابخانه‌ها غیرفعال و با تست قفل شود.

A5. §4 Auto-Fail #8 «ترکیب کد خارجی/قدیمی» ←→ LOCK-00 (import کتابخانه‌های OSS).
    تعریف «کد خارجی» نیامده. ⇒ تعریف: کپی کد از پروژهٔ دیگر ممنوع؛ import از pip/npm مجاز.

A6. §5 «YOLO-NAS via super-gradients (Apache ~50MB)» ←→ §20 (لایسنس غیرتجاری ممنوع).
    بررسی شد: کد super-gradients = Apache-2.0، اما **وزن‌های YOLO-NAS غیرتجاری و غیرقابل‌توزیع** است (LICENSE.YOLONAS.md).
    یعنی LOCK-04 خودِ پروتکل را نقض می‌کند. جزئیات در C1.

A7. §5 «madmom (BSD-3)» ←→ §20 (CC-BY-NC ممنوع).
    متادیتای PyPI پکیج madmom: `BSD, CC BY-NC-SA` (مدل‌های pretrained غیرتجاری). جزئیات در C2.

A8. §11 در چیدمان نصب، باینری `nvenc-check` دارد. چنین ابزار OSS‌ای وجود ندارد؛ ساختش = نقض LOCK-00.
    ⇒ تشخیص NVENC با `ffmpeg -hide_banner -encoders` و `ffprobe`.

A9. §15 Layer-2 هم `clippy`/`cargo test` می‌خواهد و هم `trivy`/`pa11y`/screenshot-diff؛ نه محدودهٔ تست Rust تعریف شده و نه دسترسی شبکهٔ این ابزارها تضمین است (ببینید B6).

A10. LOCK-12 (باندل ۱۰ رفرنس BB + ۱۰ رفرنس VB) ←→ §0 «فقط استفادهٔ شخصی» + §20.
    توزیع ویدیوی کپی‌رایت‌دار شخص ثالث در یک ریپوی عمومی/اینستالر = ریسک حقوقی. جزئیات در C3.

A11. §2 LOCK-04 «YOLO-NAS» ←→ §4 Auto-Fail #10 «Ollama ممنوع» بی‌ربط است، اما LOCK-04 با §20 تناقض دارد (همان A6).

---

## B. تعارض پروتکل با پلتفرم/محیط اجرا (راستی‌آزمایی‌شده)

B1. LOCK-07 / §17 «کار مستقیم روی main» ←→ من فقط روی شاخهٔ `arena/dbb53bc2-cutting-edge-studio` پوش می‌کنم؛
    ورود به `main` فقط با Pull Request. نتیجهٔ نهایی روی main یکسان است، اما یک PR در هر فاز اضافه می‌شود.

B2. در این محیط Rust/cargo نیست و `static.rust-lang.org` و `sh.rustup.rs` بلاک‌اند (کد 000).
    ⇒ پوستهٔ Tauri و در نتیجه `.exe` و NSIS اینجا **کامپایل نمی‌شود**.

B3. `huggingface.co` بلاک است (کد 000)؛ دسترسی فقط به github / npm / pypi.
    ⇒ ۱.۶۰GB وزن مدل (CLIP، whisper، Real-ESRGAN، RIFE، GFPGAN، MMAction2، PaddleOCR، TransNet) اینجا قابل تأمین نیست.
    (فقط مدل‌های داخل wheel مثل MediaPipe در دسترس‌اند.)

B4. GPU/CUDA وجود ندارد ⇒ §14 (باس‌لاین‌های عملکرد)، مسیر NVENC و رفتار OOM روی ۴GB VRAM قابل اندازه‌گیری نیست.

B5. منابع: ۲ vCPU / ۳GB RAM / ۲۰GB دیسک. نصب torch + mmcv + onnxruntime-gpu + MMAction2 عملاً ممکن نیست.
    ⇒ در این محیط فقط منطق خالص (rules) + آداپترهای نازک با fixture تست‌شدنی است؛ بقیه باید روی ماشین شما تأیید شود.

B6. `trivy` برای دیتابیس CVE به `ghcr.io` نیاز دارد و Playwright/Puppeteer برای Chromium به `storage.googleapis.com`؛
    هیچ‌کدام در allowlist نیست ⇒ گیت‌های §15 (trivy/pa11y/screenshot-diff) باید در CI اجرا شوند، نه اینجا.

B7. §16 تولید PDF (install-guide, quick-start) می‌خواهد؛ در استک تأییدشده هیچ ابزار PDF (pandoc/weasyprint) نیست.
    ⇒ یا ابزار اضافه شود یا PDF در CI ساخته شود.

B8. §16 اقلام `.exe` + `.sha256` از این محیط تولیدشدنی نیست (B2) — تصمیم شما: CI روی `windows-latest` + `build-installer.ps1` (`both`).

B9. §21 «ریپوی کاملاً خالی» ←→ واقعیت: ریپو ۱ کامیت (`Initial commit`) و ۱ فایل `README.md` (۶۶ بایت) دارد و من اجازهٔ حذف history ندارم.

B10. نام ریپو با نقطه تمام می‌شود: `Cutting-Edge-Studio.` — غیراستاندارد و می‌تواند برخی ابزارها/URLها را بشکند.

B11. اپ دسکتاپ Tauri در پیش‌نمایش مرورگر قابل نمایش نیست؛ فقط UI وبی (Vite) قابل Preview است ⇒ مسیر تأیید بصری UI.

B12. §16 هیچ اشاره‌ای به code-signing ندارد؛ `.exe` بدون امضا در ویندوز هشدار SmartScreen می‌دهد.

B13. §11 «sidecar.exe + python-embed + _internal» یعنی PyInstaller — که خودش لایسنس GPL دارد (C6).

---

## C. حقوقی / لایسنس

C1. **YOLO-NAS (LOCK-04) نقض §20.** کد Apache-2.0 اما وزن‌ها: غیرتجاری، توزیع ممنوع، فقط از CDN دِسی دانلود می‌شوند
    (یعنی هم لایسنس غیرتجاری و هم دانلود runtime = دو Auto-Fail).
    ⇒ جایگزین‌های Apache-2.0 با وزن‌های آزاد: YOLOX، RT-DETR، PP-YOLOE (PaddleDetection)، DAMO-YOLO.
    اگر LOCK-04 ماند، توزیع وزن‌ها ممنوع است و تنها مسیر قانونی، وزن‌های خودآموزش‌یافته است (که §4 آن را ممنوع کرده) ⇒ بن‌بست.

C2. **madmom.** کد BSD-3/CC BY-NC-SA؛ مدل‌های pretrained غیرتجاری ⇒ در لیست سیاه §20.
    ضمناً برای Python 3.11 wheel ندارد و با numpy 2 می‌شکند (D1).
    ⇒ جایگزین: librosa (ISC) beat tracking + scipy.signal.find_peaks، یا Beat-This (MIT).

C3. **رفرنس‌ها و موزیک باندل‌شده (LOCK-12 + §11).** ۱۰+۱۰ ویدیوی مرجع و ~۳۵۰MB موزیک، آثار شخص ثالث‌اند.
    توزیع آن‌ها در ریپوی عمومی/اینستالر بدون اجازهٔ کتبی = نقض کپی‌رایت (حتی برای استفادهٔ شخصی، «توزیع» ممنوع است).
    ⇒ الف) رفرنس‌ها فقط توسط کاربر import شوند (بدون باندل)؛ ب) موزیک فقط CC0/CC-BY با attribution؛
    ج) یا باندل رفرنس حذف و به‌جایش «راهنمای انتخاب رفرنس» + اسکریپت دانلود محلی.

C4. **FFmpeg.** BtbN هم بیلد GPL دارد هم LGPL؛ `libx264` = GPL. باید دقیقاً واریانت LGPL shared پین شود،
    وگرنه Auto-Fail #4. مسیر H.264 بدون GPL: NVENC (کارت شما پشتیبانی می‌کند) یا openh264.

C5. **CUDA / cuDNN DLLها** (حدود ۱.۵–۲GB) تحت لایسنس انحصاری NVIDIA توزیع می‌شوند، در whitelist نیستند
    و در بودجهٔ ۳.۰GB هم حساب نشده‌اند. نیاز به تصمیم صریح.

C6. **PyInstaller** = GPLv2+ با استثنای bootloader (در whitelist نیست) ⇒ یا استثنا پذیرفته شود یا مسیر بسته‌بندی عوض شود.

C7. **python-embed 3.11** = لایسنس PSF (در whitelist نیست) ⇒ باید اضافه شود.

C8. **فونت‌ها** Vazirmatn/Inter/JetBrains Mono = OFL 1.1 (در whitelist نیست) ⇒ باید اضافه شود.

C9. **face_recognition → dlib** = Boost License (در whitelist نیست). ضمناً کامپایلش سنگین است.

C10. **PaddleOCR → paddlepaddle**: کد Apache اما حجم/ABI ویندوز و لایسنس خود فایل‌های مدل باید جدا بررسی شود.

C11. **TransNet V2**: کد MIT، اما checkpoint در Google Drive/HF میزبانی می‌شود ⇒ آینهٔ محلی + یادداشت لایسنس لازم است.

C12. **GFPGAN / Real-ESRGAN / RIFE**: کد BSD/Apache، اما وزن‌ها روی دیتاست‌هایی مثل FFHQ (CC BY-NC-SA 4.0) آموزش دیده‌اند
    ⇒ ریسک لایسنس مشتق؛ نیاز به تأیید حقوقی یا حذف GFPGAN.

C13. **صداهای Piper**: هر voice لایسنس خودش را دارد (بعضی CC-BY، بعضی research-only) ⇒ audit تک‌تک صداها.

C14. **Kinetics-400 checkpoint (MMAction2)**: لایسنس وزن‌ها به‌ازای هر config متفاوت است ⇒ بررسی موردی.

C15. **Qwen2.5-Coder-3B** = Apache-2.0 (بدون مشکل)، اما URL و SHA-256 پین‌شده لازم است.

---

## D. وابستگی‌های شکسته / در حال فرسودن

D1. **madmom 0.16.1**: نسخهٔ ۲۰۱۸، بدون wheel برای cp311، استفاده از `np.float` حذف‌شده ⇒ روی python-embed 3.11 نصب/اجرا نمی‌شود.

D2. **super-gradients 3.7.1**: بعد از خرید دِسی توسط NVIDIA نگهداری نمی‌شود؛ پین‌های torch/hydra کهنه و دانلود خودکار وزن.

D3. **MMAction2 1.2.0** به mmcv/mmengine وابسته است؛ کامپایل mmcv روی ویندوز دردناک و wheel رسمی برای همهٔ ترکیب‌های torch/CUDA نیست.

D4. **onnxruntime + torch + whisper + CLIP + GFPGAN روی ۴GB VRAM** هم‌زمان جا نمی‌شوند ⇒ سیاست load/unload ترتیبی + fallback CPU اجباری است.

D5. `filterwarnings = ["error"]` + numpy 2 در برابر کتابخانه‌هایی که هنوز `np.float`/`np.int` استفاده می‌کنند ⇒ تست‌ها روی import می‌شکنند.

D6. **react-timeline-editor** (DOM-based) برای «۵۰۰+ کلیپ با ۶۰fps» واقع‌بینانه نیست؛ تایم‌لاین باید canvas/Konva + virtualization باشد.
    ⇒ یا هدف §14 تعدیل شود یا تایم‌لاین روی Konva (که در استک هست) بازنویسی شود.

D7. **GTX 1650 (Turing)**: NVENC فقط H.264 (بدون AV1/B-frame) ⇒ پریست‌های خروجی §7 Stage 11 باید همین را منعکس کنند.

D8. **PyInstaller sidecar** + مدل‌های بزرگ = آنتی‌ویروس‌های ویندوز به‌راحتی false positive می‌دهند؛ امضای کد لازم می‌شود.

---

## E. مشخصات ناقص / معیار پذیرش نامشخص

E1. «۸۵–۹۵٪ اتوماسیون»، «۸۵–۹۰٪ حرفه‌ای»، «۸۵٪+ تطابق با رفرنس»: هیچ متریک، هیچ ground truth، هیچ دیتاست مرجع تعریف نشده.
    ⇒ لازم است: ۱۰ کلیپ + ۱ رفرنس شما به‌عنوان Golden Set + متریک عددی (مثلاً شباهت توزیع طول کات‌ها، دقت نوع نما، F1 هم‌ترازی بیت).

E2. Stage 4 (CompatibilityReport) هیچ schema/فیلدی ندارد.

E3. سه قرارداد حیاتی بدون schema: `StyleDNA.json`، `SourceAnalysis.json`، `EDL.json` / `EDL_v2.json`.
    من باید تعریفشان کنم و شما تأیید کنید، وگرنه P6 قابل تست نیست.

E4. §4 Auto-Fail #1 «mask کردن خطا» تعریف ندارد (چه چیزی mask است؟ try/except کلی؟).

E5. پوشش ≥۸۰٪ برای آداپترهای نازک OSS یعنی mock سنگین؛
    ⇒ قرارداد: unit test روی منطق خالص + contract test با fixture ضبط‌شده برای آداپترها.

E6. آستانه‌های BB (زانو/شانه ۳۵° و ۱۶۰°) با landmarkهای ۲بعدی MediaPipe به زاویهٔ دوربین و انسداد حساس‌اند
    ⇒ tolerance + confidence gating + کالیبراسیون لازم است.

E7. نگاشت VB به کلاس‌های Kinetics-400: باید با label map دقیق همان checkpoint تأیید شود (۴۰۰/۶۰۰/۷۰۰ تفاوت دارند).

E8. §10 تم GLASS «particles + glow» با LOCK-00 (بدون گرافیک از صفر) در تضاد است ⇒ فقط CSS، بدون canvas سفارشی.

E9. هیچ مشخصاتی برای diagnostics آفلاین (لاگ/باندل خطا) و صفحهٔ خطا وجود ندارد.

E10. **WebView2**: توزیع ویندوز بدون runtime وب‌ویو Tauri اجرا نمی‌شود؛ bootstrapper نیاز به دانلود دارد (نقض آفلاین)
    ⇒ باید Fixed-Version Runtime (~۱۸۰MB) در اینستالر باندل شود.

E11. رفتار uninstall برای دادهٔ کاربر (`%APPDATA%/CuttingEdgeV2`) تعریف نشده.

E12. RTL برای متن روی canvas (تایم‌لاین/اورلی) مشخص نشده؛ Vazirmatn در Konva/SVG نیاز به shaping دارد.

---

## F. اعداد و حسابداری

F1. جمع ساعت‌های §6: 18+28+22+18+20+26+45+35+25+25 = **۲۶۲ ساعت**، در حالی که پروتکل ۱۸۰–۲۴۰ ساعت می‌گوید ⇒ ۲۲ ساعت بیش از سقف.

F2. بودجهٔ ۳.۰GB شامل CUDA/cuDNN (~۱.۵GB) + WebView2 (~۱۸۰MB) + موزیک/بی‌رول اختیاری (۵۰۰MB) نیست ⇒ اینستالر واقعی ≈ ۴.۷–۵GB.

F3. §14 «Style Match خروجی ۲ دقیقه ≈ ۲۰ دقیقه روی GTX 1650» فقط با بارگذاری ترتیبی مدل‌ها ممکن است؛ اندازه‌گیری لازم دارد.

F4. ۲۶۰ استپ در ۱۱ هفته = ~۲۴ استپ/هفته، با فرض صفر تأخیر در تأیید شما؛ با LOCK-19 تقویم واقع‌بینانه نیست.

F5. §6 جمع استپ‌ها = ۲۶۰ ✓ (این یکی درست است) — فقط ساعت‌ها و تقویم نمی‌خواند.

---

## G. تصمیم‌های لازم از Owner (بلوکه‌کننده)

G1.  شاخه: تأیید مدل «شاخهٔ نشست + PR به main» (B1) یا توقف کامل.
G2.  LOCK-04: جایگزینی YOLO-NAS با YOLOX/RT-DETR/PP-YOLOE (C1) یا پذیرش ریسک حقوقی.
G3.  madmom: حذف و جایگزینی با librosa/Beat-This (C2, D1).
G4.  رفرنس‌ها/موزیک: باندل حذف شود و کاربر import کند (C3) یا لایسنس کتبی.
G5.  FFmpeg: پین واریانت LGPL + مسیر H.264 = NVENC/openh264 (C4).
G6.  CUDA/cuDNN: باندل شود (حجم+لایسنس)، یا نسخهٔ CPU-only به‌عنوان پیش‌فرض و GPU اختیاری (C5, F2).
G7.  whitelist: PSF، OFL 1.1، Boost، PyInstaller-exception اضافه شود (C6–C9).
G8.  WebView2 offline runtime باندل شود (E10) و بودجهٔ حجم اصلاح شود (F2).
G9.  باندل ساعت: ۲۶۲h واقعی است یا باید scope کم شود (F1).
G10. §13/§18: Evidence Report مجاز شمرده شود (A1).
G11. §19 در برابر all_source: توقف فازی یا پیوسته (A2).
G12. Golden Set: ۱۰ کلیپ + ۱ رفرنس + تعریف متریک عددی (E1).
G13. schemaهای StyleDNA/SourceAnalysis/EDL تأیید شوند (E3).
G14. code-signing: امضا می‌شود یا SmartScreen پذیرفته است (B12).
G15. PDFها: تولید در CI مجاز است یا باید حذف شوند (B7).
G16. منابع مالی/فیزیکی: ماشین ویندوز برای تأیید نهایی (GTX 1650) در دسترس شما هست یا نه.

---
---

# ✅ RESOLUTION LOG — Protocol v2.5 → v2.5.1

تصمیم‌های Owner در تاریخ 2026-11-04. از این پس **v2.5.1** مرجع است.
هیچ موردی از A/B/C/D/E/F باز باقی نمانده است.

| ID  | موضوع | تصمیم نهایی Owner | اثر روی پیاده‌سازی |
|-----|-------|-------------------|---------------------|
| G1 / B1 | شاخه | شاخهٔ نشست + PR به main، هر فاز یک PR | LOCK-07 اصلاح شد؛ CI/PR اجباری |
| G2 / C1 | YOLO-NAS | حذف → **YOLOX** (کد Apache-2.0، وزن MIT، ~35MB، وزن از GitHub Releases)؛ fallback: RT-DETR | LOCK-04 = YOLOX؛ آداپتور `detection/yolox.py` |
| G3 / C2 / D1 | madmom | حذف → **librosa (ISC) + scipy.signal (BSD-3)**؛ fallback Beat-This (MIT) | beat/onset/tempo از librosa |
| G4 / C3 | رفرنس/موزیک | باندل حذف → **user-import** در `%APPDATA%/CuttingEdgeV2/references` و `/music` | LOCK-12 = user-import؛ UI drag-drop |
| G5 / C4 | FFmpeg | فقط **LGPL shared** (BtbN) با SHA-256 پین‌شده؛ H.264 = NVENC، fallback openh264 (BSD-2)؛ libx264 ممنوع | resolver باینری + تست encoder |
| G6 / C5 / F2 | CUDA | **CPU-only پیش‌فرض** (onnxruntime)؛ GPU اختیاری با تشخیص `nvidia-smi` | بودجهٔ مدل ~1.15GB؛ سوئیچ در Settings |
| G7 / C6–C9 | Whitelist | +**PSF**, +**OFL 1.1**, +**Boost**, +**PyInstaller-Bootloader-Exception** | `licenses/THIRD-PARTY.md` |
| G8 / E10 | WebView2 | **Fixed-Version Runtime** باندل (~180MB)؛ Evergreen ممنوع | بودجهٔ اینستالر → **3.5GB** |
| G9 / F1 | ساعت | **180–262h** واقعی؛ تقویم 11–13 هفته | برنامه‌ریزی |
| G10 / A1 | §13 | **6 نوع پیام** مجاز (+Evidence Report) | گزارش فازی |
| G11 / A2 | LOCK-19 | **توقف فازی باقی است**؛ «all_source» باطل | تأیید Owner در هر گیت |
| G12 / E1 | Golden Set | ۱۰ کلیپ BB + ۱ رفرنس؛ ۵ متریک: KS-test طول کات، F1 نوع نما، beat<100ms، Pearson r>0.7، ΔE<10؛ قبولی = ۳ از ۵ | `services/stylematch/metrics.py` |
| G13 / E3 | Schemaها | Builder پیشنهاد می‌دهد، Owner approve می‌کند (JSON Schema draft-07 + مثال) | P6-S01 blocker gate |
| G14 / B12 | Code signing | **انجام نمی‌شود**؛ SmartScreen پذیرفته + `docs/bypass-smartscreen.md` | مستندسازی |
| G15 / B7 | PDF | حذف → **Markdown** برای همهٔ مستندات | `delivery/*.md` |
| G16 | ماشین تست | GTX 1650 + i5-12400 + 16GB + CUDA 12.x در دسترس Owner | تست integration/عملکرد سمت Owner |
| D4 | VRAM | load/unload ترتیبی، یک مدل سنگین هم‌زمان؛ priority: MediaPipe > CLIP > YOLOX > بقیه | `services/inference/registry.py` |
| D6 | تایم‌لاین | react-timeline-editor برای MVP؛ هدف واقعی 100–200 کلیپ smooth؛ بازنویسی از صفر ممنوع | P2 |
| D7 | NVENC | فقط H.264 High Profile؛ بدون AV1/B-frame؛ fallback openh264 | پریست‌های خروجی |
| D8 | آنتی‌ویروس | در install-guide ذکر شود؛ استثنای پوشهٔ نصب | مستندات P9 |
| E4 | Error masking | try/except بدون `structlog.error` + پیام کاربر = mask (ممنوع) | ruff rule + review |
| E8 | GLASS theme | فقط CSS (`backdrop-filter`, `box-shadow`, gradient)؛ canvas/WebGL ممنوع؛ tsParticles حذف | P1 |
| E11 | Uninstall | NSIS دادهٔ `%APPDATA%` را نگه می‌دارد؛ گزینهٔ «Also remove user data» (پیش‌فرض خاموش) | P9 |
| E12 | RTL canvas | `Konva.Text{direction:'rtl', fontFamily:'Vazirmatn'}`؛ SVG با `direction`+`unicode-bidi` | P7 + تست P8 |
| B13 | بسته‌بندی | PyInstaller با bootloader exception؛ fallback cx_Freeze (PSF) | `scripts/build-installer.ps1` |

## تغییرات رسمی v2.5.1
```
LOCK-04 : YOLO-NAS → YOLOX (Apache-2.0 code + MIT weights); fallback RT-DETR
LOCK-07 : کار مستقیم روی main → شاخهٔ نشست + PR
LOCK-12 : 20+ references باندل‌شده → user-imported references
§5      : madmom → librosa + scipy.signal
§5      : YOLO-NAS → YOLOX
§5      : onnxruntime-gpu → onnxruntime (CPU) پیش‌فرض، GPU اختیاری
§11     : حجم ~3.0GB → ~3.5GB (WebView2 fixed-version)
§11     : llm/ و references/ و music/ = user-populated
§13     : 5 → 6 نوع پیام (+Evidence Report)
§16     : PDF → Markdown
§20     : +PSF, +OFL 1.1, +Boost, +PyInstaller-Bootloader-Exception
Budget  : 180–240h → 180–262h
```

## R-1. New Risk (P2) — `react-timeline-editor` از npm حذف شده است

`npm view react-timeline-editor` → **E404 Unpublished on 2022-06-18**. یعنی کتابخانه‌ای که
LOCK-00/§5 به‌عنوان تایم‌لاین MVP نام برده، دیگر قابل نصب نیست.

**تصمیم (بدون نیاز به تأیید، چون جایگزین همان کتابخانه است):**
`@xzdarcy/react-timeline-editor@1.0.0` — همان نویسنده، همان مخزن (`github.com/xzdarcy/react-timeline-editor`)،
لایسنس **MIT**، `peerDependencies: react >= 18`. وابستگی‌های فرعی: `@xzdarcy/timeline-engine` (ISC) و
`react-virtualized` (MIT) — هر دو در whitelist.

اگر این وابستگی در عمل ناپایدار شد، مسیر پشتیبان (بدون نوشتن تایم‌لاین از صفر):
`dnd-timeline@3.1.1` (MIT، ساخته‌شده روی dnd-kit که همین حالا در استک است).
