# گزارش سخت‌سازی (Hardening) — ۲۰۲۶-۱۱-۰۷

> **Branch:** `arena/dbb53bc2-cutting-edge-studio` · **CI:** `zizmor 1.32.0` → **No findings** (قبل: ۳۱ مورد: ۲۱ HIGH unpinned + ۴ LOW artipacked + ۶ MEDIUM permissions)
> **Commit:** این PR — ادامهٔ `17f2ef1` (Audit Fix Report)

## خلاصه ۱۰ مورد

| # | دسته | قبل | بعد | وضعیت |
|---|---|---|---|---|
| 1 | 🔴 **Actions بدون pin** — ۲۰→۲۱ مورد `@v4`/`@v5`/`@stable` بدون SHA | هر push تگ متحرک می‌توانست کد مخرب تزریق کند | ✅ همه ۱۸ مورد به SHA پین: `checkout@11d5960`, `setup-python@a26af69`, `setup-node@49933ea`, `download-artifact@d3f86a`, `upload-artifact@ea165f8`, `trivy@ed142fd`, `rust-toolchain@b725eda`, `rust-cache@d1527c8` + `dependabot.yml` هفتگی | **رفع کامل** |
| 2 | 🟠 **Artipacked بدون `persist-credentials:false`** — ۴ checkout | token در git config باقی می‌ماند، upload-artifact می‌تواند exfiltrate کند | ✅ هر ۴ `checkout` با `persist-credentials: false` | **رفع کامل** |
| 3 | 🟠 **Jobs بدون `permissions:`** — ۶ مورد | `GITHUB_TOKEN` با write-all پیش‌فرض | ✅ `permissions: contents: read` در workflow + هر job (desktop-evidence: `actions:read` اضافه) | **رفع کامل** |
| 4 | 🟡 **Adhoc `npm install playwright-core@1.64.1`** — خارج از lockfile | بدون integrity، هر build نسخهٔ متفاوت | ✅ `scripts/ci/webview-tools/package.json` + `package-lock.json` با `sha512-BC4s8…` و `npm ci` از lockfile | **رفع کامل** |
| 5 | 🔴 **تست ضعیف — substring به جای golden** — `69%` موتانت زنده (۴/۶) | `a=0→a=1`, `-an→-c:a` برمی‌گشت و تست سبز می‌ماند | ✅ `backend/tests/test_render_command_golden.py` — ۹ تست golden با `filter_complex == GOLDEN_…` دقیق، `6/6` موتانت kill (شامل `default bitrate 12000` و `clamp 0.05`) | **رفع کامل** |
| 6 | 🟡 **پیچیدگی بالا** — `detect_pose_type E33`, `parse_probe E31`, `build_edl_command D22` | `radon cc` هشدار — ریسک نگهداری | ⏳ مستندسازی + پذیرش موقت — refactor نیاز PR جداگانه (برنامه: تجزیه `build_edl_command` به `_build_inputs/_build_graph`) | **باز — پذیرفته‌شده** |
| 7 | 🟣 **mypy strict دروغین** — `strict=false + ۱۱ ماژول ignore_errors` (در strict واقعی ۲۶ خطا) | type safety ادعایی، CI نوعی نداشت | ✅ صادقانه: `mypy app` در CI با `strict=false` (۰ خطا، ۷۲ فایل) + مستندسازی ۲۶ خطای strict به عنوان بدهی فنی | **باز — صادقانه** |
| 8 | 🟠 **بدون ffmpeg واقعی در CI** — فقط argv | دستور می‌سازیم ولی هیچ‌وقت اجرا نمی‌کنیم | ✅ `sudo apt-get ffmpeg` + `ffmpeg -f lavfi testsrc … /tmp/smoke.mp4 + ffprobe` در job backend | **رفع کامل** |
| 9 | 🟡 **نام ریپو با نقطه** — `Cutting-Edge-Studio.` | Win32 نقطهٔ انتهایی را حذف می‌کند، clone پیش‌فرض شکست | ✅ workaround مستند در `ci.yml` (`C:\build` + `git clone`) + تلاش `gh api PATCH` → ۴۰۳ (نیاز admin) ثبت شد | **باز — workaround** |
| 10 | 🟡 **موتیشن فقط render.py** — سایر ماژول‌ها تست‌نشده | پوشش جهش ۱ ماژول | ⏳ مستند — مرحلهٔ بعد: cosmic-ray روی `pose_geometry`, `probe`, `orchestrator` | **باز — برنامه‌ریزی** |

## جزئیات فنی

### ۱. پین SHA
منبع SHAها از `api.github.com` و dereference تگ‌های annotated (مثلاً `trivy v0.36.0: tag a9c7b0f → commit ed142fd`). اعتبارسنجی:
```
checkout 11d5960a326750d5838078e36cf38b85af677262 ✓
setup-python a26af69be951a213d495a4c3e4e4022e16d87065 ✓
trivy tag a9c7b0f → ed142fd0673e97e23eac54620cfb913e5ce36c25 ✓
rust-cache tag e9d7b9f → d1527c8f67ef9af357290475d4af4b0fab8f12e0 ✓
```
Dependabot هفتگی (`cooldown: 7 days`) پین‌ها را به‌روز نگه می‌دارد.

### ۲-۳. hardening zizmor
قبل: `21 error[unpinned-uses], 4 warning[artipacked], 6 warning[excessive-permissions]`
بعد: `No findings to report. Good job!`

### ۴. lockfile
`scripts/ci/webview-tools/package-lock.json` با `integrity: sha512-BC4s8y…` — در CI با `npm ci --prefix $RUNNER_TEMP/ce-webview-tools` نصب می‌شود (فایل‌های اصلی از `C:\build` کپی).

### ۵. golden tests
قبل: `assert "concat=n=2:v=1:a=1" in joined` — موتانت `a=0→a=1` را نمی‌گرفت.
بعد: `assert _filter_complex(cmd) == GOLDEN_BASIC_2SEG` + ۸ سناریو: basic audio, silent, subtitles+loudness, clamp tiny, speed 2x, default bitrate, single segment, has_audio flag, full argv equality.

### ۸. ffmpeg smoke
در `backend` job بعد از `pip-audit`:
```yaml
sudo apt-get install -y ffmpeg
ffmpeg -f lavfi -i testsrc=duration=1:size=128x128:rate=30 -frames:v 1 -c:v libx264 -pix_fmt yuv420p /tmp/smoke.mp4 -y
ffprobe -hide_banner /tmp/smoke.mp4
```

## تست‌های محلی
- `zizmor .` → No findings
- `ruff check` → ۰ خطا (۱ فایل reformat شد)
- `mypy app` → Success 72 files
- `pytest --cov` → 92.47% (392 tests, شامل ۹ golden جدید)
- `frontend: lint/test/build` → 168 passed, build success

## بدهی فنی باقی‌مانده (غیرمسدود)
۶ و ۷ و ۹ و ۱۰ عمداً باز گذاشته شده‌اند — هرکدام نیاز تصمیم معماری یا دسترسی admin دارد و در PR جداگانه بهتر است. هیچ‌کدام امنیت supply-chain را تهدید نمی‌کند.
