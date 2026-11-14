# FINN Loop — چرخهٔ خودرانِ ساخت «Muscle Paradise» بدون نظارت انسانی

> نسخه: ۱.۰ | تاریخ: ۲۰۲۶-۱۱-۱۴
> ورودی این سند: `16_LAYER_PRODUCTION_PLAN.md` (طرح تولید ۱۶ لایهٔ Muscle Paradise)
> این سند **خوداجرا (self-executing)** است: هر ایجنت هوش مصنوعی که آن را بخواند، مجری لوپ است و بدون نیاز به نظارت انسان تا شرط پایان پیش می‌رود.
> **F.I.N.N = Forge → Inspect → Normalize → Next** (ساخت → بازبینی → نرمال‌سازی → گام بعد)

---

## ۰. قرارداد اجرا — بخوان و بپذیر

این سند یک «پروتکل اجرای خودکار» است، نه توصیه. هر ایجنت هوش مصنوعی (Claude Code، Arena، یا هر عامل دیگر) که این سند را در فضای کاری اجرا می‌کند:

1. **قبل از هر کاری، فاز ۰ (نصب ECC) را اجرا می‌کند** — بدون ECC لوپ شروع نمی‌شود.
2. میکرو-چرخه‌ها را **پشت سر هم** (M00 → M01 → … → M17) طی می‌کند؛ هیچ چرخه‌ای بدون سبزشدن گیت‌هایش تمام نمی‌شود.
3. در هر گام، **ایجنت مشخص‌شده از ECC** را فراخوانی می‌کند (جدول بخش ۵ و ۶).
4. هر خطا را **دیباگ** می‌کند، هر درس را در Ledger می‌نویسد و **هرگز اشتباه قبلی را تکرار نمی‌کند**.
5. هیچ‌وقت برای پرسیدن سؤال از انسان متوقف نمی‌شود؛ در ابهام، تصمیم می‌گیرد، در `DECISIONS.md` ثبت می‌کند و ادامه می‌دهد.
6. کیفیت هر چرخه باید در سطح **کلاس جهانی** باشد (تعریف عملیاتی: بخش ۱۰).

---

## ۱. میدان اجرا

- **محصول:** Muscle Paradise (MP) — طبق `16_LAYER_PRODUCTION_PLAN.md` (همین پوشه).
- **ریپازیتوری هدف طبق طرح:** `github.com/yousefghorbanian98-create/Chat2DB` — کد جدید فقط زیر `mp-app/` و مستندات زیر `docs/MuscleParadise/`؛ پوشهٔ `ce-app/` هرگز دست نمی‌خورد.
- این پروتکل **repo-agnostic** است: در هر مخزنی اجرا شود، همان چیدمان `mp-app/` + `docs/MuscleParadise/` را می‌سازد.
- ممنوع: push به شاخه‌های دیگر، دست‌کاری `ce-app/`، حذف تاریخچهٔ git.

---

## ۲. قوانین طلایی لوپ (غیرقابل مذاکره)

| # | قانون |
|---|--------|
| G1 | **توقف ممنوع** — تا رسیدن به شرط پایان (بخش ۱۱) از انسان چیزی پرسیده نمی‌شود؛ ابهام = تصمیم خودمختار + ثبت در `DECISIONS.md`. |
| G2 | **هیچ گیت قرمزی رد نمی‌شود** — تست شکسته، لینت خطا، یا اسکن امنیتی آلوده = چرخه تمام نشده. skip/ignore ممنوع. |
| G3 | **هر باگ = یک تست رگریشن** — باگ رفع‌شده بدون تست، «رفع‌نشده» حساب می‌شود. |
| G4 | **حداکثر ۳ تلاش رفع** برای هر خطا؛ بعد از سومین شکست: rollback میکرو-چرخه، بازطراحی با `planner`، سپس از سرگیری. |
| G5 | **هر میکرو-چرخه = یک commit** با پیام استاندارد؛ هیچ کار نیمه‌کاره‌ای بین چرخه‌ها باقی نمی‌ماند. |
| G6 | **Anti-Dup** — قبل از ساخت هر چیزی، جست‌وجوی کد موجود (Grep/Glob)؛ ساختن ماژول تکراری ممنوع. |
| G7 | **Ledger اجباری** — آغاز هر میکرو-چرخه با خواندن کامل `LEDGER.md`؛ پایان هر چرخه با به‌روزرسانی آن. |
| G8 | **LLM تصمیم‌گیرندهٔ عدد نیست** — در محصول MP، بار/ست/تکرار فقط از موتور قواعد می‌گذرد (قانون طرح ۱۶ لایه، لایهٔ ۱۵). |
| G9 | **هر تصمیم معماری = یک ADR** در `docs/MuscleParadise/adr/` + رکورد در `DECISIONS.md`. |
| G10 | **پایان فقط با گزارش نهایی** — `finn/FINAL_REPORT.md` با شواهد (خروجی تست‌ها، پوشش، اسکن‌ها) تولید می‌شود، نه ادعای متنی. |

---

## ۳. فاز ۰ — نصب ECC (الزامی، قبل از شروع لوپ)

**ECC = Everything Claude Code** — `github.com/WorldFlowAI/everything-claude-code` (MIT، ۶۰۰۰+ ستاره؛ مجموعهٔ ایجنت‌ها، فرمان‌ها، اسکیل‌ها، قوانین و هوک‌های Claude Code).

### ۳.۱ نصب خودکار (روش پیش‌فرض — یک دستور)

```bash
bash docs/MuscleParadise/finn/install-ecc.sh
```

اسکریپت: ECC را در `.finn/ecc/` کلون می‌کند (کامیت در `.finn/ecc-commit.txt` ثبت می‌شود)، مؤلفه‌ها را در `.claude/` نصب می‌کند، فایل‌های وضعیت لوپ را در `.finn/state/` می‌سازد و وجود ۹ ایجنت را تأیید می‌کند.

### ۳.۲ روش دستی (اگر اسکریپت اجرا نشد)

```bash
git clone --depth 1 https://github.com/WorldFlowAI/everything-claude-code.git .finn/ecc
cp -R .finn/ecc/agents   .claude/agents
cp -R .finn/ecc/commands .claude/commands
cp -R .finn/ecc/skills   .claude/skills
cp -R .finn/ecc/rules    .claude/rules
cp -R .finn/ecc/hooks    .claude/hooks
```

### ۳.۳ روش پلاگین (در محیط‌های Claude Code)

`/plugin marketplace add WorldFlowAI/everything-claude-code` سپس نصب پلاگین — معادل روش بالا.

### ۳.۴ قاعدهٔ «فراخوانی ایجنت» در هر محیط

- **در Claude Code:** هر ایجنت با نامش فراخوانی می‌شود (subagent): `planner`، `architect`، `tdd-guide`، `code-reviewer`، `security-reviewer`، `build-error-resolver`، `e2e-runner`، `refactor-cleaner`، `doc-updater`.
- **در هر محیط عمومی دیگر (مثل Arena یا چت):** ایجنت = **نقش‌آفرینی بر اساس فایل `.claude/agents/<name>.md>`** — یعنی برای هر گام، محتوای همان فایل (دستورالعمل سیستمی + فرایندش) خوانده می‌شود و مجری دقیقاً با همان نقش و روش‌شناسیِ آن ایجنت کار می‌کند. خروجی هر گام باید نشان دهد «کدام ایجنت» اجرا شده است.
- **فرمان‌ها** (`/plan`، `/tdd`، `/code-review`، `/e2e`) و **اسکیل‌ها** (`verification-loop`، `security-review`، `tdd-workflow`، `backend-patterns`، `coding-standards`) به‌عنوان چک‌لیست هر گام استفاده می‌شوند.

### ۳.۵ تأییدیهٔ فاز ۰ (چک‌لیست — همه باید ✓ باشند)

- [ ] ۹ فایل ایجنت در `.claude/agents/` موجودند (planner, architect, tdd-guide, code-reviewer, security-reviewer, build-error-resolver, e2e-runner, refactor-cleaner, doc-updater)
- [ ] کامیت ECC در `.finn/ecc-commit.txt` ثبت شده
- [ ] فایل‌های وضعیت `LEDGER.md`، `STATE.md`، `DECISIONS.md`، `REGRESSIONS.md` ساخته شده‌اند
- [ ] `git status` تمیز commit شده (فقط اسکریپت و مستندات — `.finn/` و `.claude/` در `.gitignore`)

---

## ۴. ماشین‌آلات لوپ (حافظه و ضدتکرار)

| فایل | نقش | قاعده |
|------|------|--------|
| `.finn/state/STATE.md` | وضعیت جاری: چرخه، شمارنده تلاش، آخرین گیت سبز | هر گام به‌روزرسانی شود |
| `.finn/state/LEDGER.md` | جدول درس‌ها/باگ‌ها/قانون‌های «هرگز تکرار نشود» | **آغاز هر چرخه کامل خوانده شود**؛ فقط append |
| `.finn/state/DECISIONS.md` | ثبت تصمیم‌های خودمختار | هر تصمیم بدون نظارت انسان |
| `.finn/state/REGRESSIONS.md` | رجیستری تست‌های رگریشن | هر باگ = یک ردیف + تست واقعی |
| `docs/MuscleParadise/adr/NNNN-*.md` | ADRهای معماری | هر تصمیم لایهٔ ۲/۳/۴ |
| `finn/FINAL_REPORT.md` | گزارش پایانی با شواهد | فقط در M17 |

---

## ۵. چرخهٔ درونی FINN — آناتومی هر میکرو-چرخه

هر میکرو-چرخه (M01 … M17) دقیقاً ۴ فاز را طی می‌کند:

```
┌────────────────────────────────────────────────────────────┐
│  F — Forge (ساخت)                                          │
│  planner → architect → tdd-guide → پیاده‌سازی →            │
│  build-error-resolver (تا سبزشدن build/test)               │
├────────────────────────────────────────────────────────────┤
│  I — Inspect (بازبینی)                                     │
│  code-reviewer (چک‌لیست کیفیت) → اجرای کامل تست‌ها →       │
│  e2e-runner (مسیرهای حیاتی)                                │
├────────────────────────────────────────────────────────────┤
│  N — Normalize (نرمال‌سازی)                                │
│  refactor-cleaner (حذف تکرار/کد مرده) → security-reviewer   │
│  (OWASP + bandit/pip-audit) → build-error-resolver نهایی    │
├────────────────────────────────────────────────────────────┤
│  N — Next (گام بعد)                                        │
│  doc-updater (مستندات + CHANGELOG) → به‌روزرسانی LEDGER/    │
│  STATE/REGRESSIONS → commit → چرخهٔ بعد                    │
└────────────────────────────────────────────────────────────┘
```

### گیت‌های پایان هر میکرو-چرخه (Definition of Done) — همه اجباری

1. ✅ build بدون خطا (`pytest` / `flutter test` / `npm run build` بسته به لایه)
2. ✅ پوشش تست بک‌اند ≥ ۷۰٪ (طبق لایهٔ ۱۴ طرح) — بدون کاهش نسبت به چرخهٔ قبل
3. ✅ لینت و فرمت تمیز (`ruff`، `eslint`، `dart analyze`)
4. ✅ `bandit` + `pip-audit` بدون خطای بحرانی جدید
5. ✅ گزارش `code-reviewer` بدون یافتهٔ Blocker
6. ✅ تست‌های رگریشن (رجیستری) همه سبز
7. ✅ مستندات + CHANGELOG به‌روز (`doc-updater`)
8. ✅ LEDGER به‌روز شده؛ هیچ «درس تکراری» جدیدی ثبت نشده (درس تکراری = شکست چرخه)
9. ✅ یک commit با پیام `mp(Mxx): <summary> [finn]`

---

## ۶. نگاشت ۱۶ لایهٔ طرح → میکرو-چرخه‌های FINN

ترتیب **ترتیبی (sequential)** است؛ هر چرخه روی خروجی چرخهٔ قبل می‌سازد.

| چرخه | لایه/موضوع | خروجی اصلی | ایجنت‌های ECC (به ترتیب) |
|-------|-----------|-------------|---------------------------|
| **M00** | بوت‌استراپ | نصب ECC + اسکلپ پروژه `mp-app/` + CI اولیه | — (اسکریپت فاز ۰) |
| **M01** | ۱ — PRD | `docs/MuscleParadise/PRD.md` + user-stories با Given/When/Then | `planner` → `doc-updater` |
| **M02** | ۲ — معماری | ADR-001..004 + C4 متنی + ساختار ماژول‌ها | `architect` → `code-reviewer` → `doc-updater` |
| **M03** | ۳ — دیتابیس | مدل‌های SQLAlchemy + migrationهای Alembic + ایندکس‌ها | `architect` → `tdd-guide` → `build-error-resolver` |
| **M04** | ۴ — قرارداد API | `mp-app/backend/api/v1/` + OpenAPI + rate-limit | `planner` → `tdd-guide` → `build-error-resolver` |
| **M05** | ۵ — بک‌اند هسته | ماژول‌های membership/assessment/payments (Router→Service→Repository) + APScheduler + structlog | `tdd-guide` → `code-reviewer` → `security-reviewer` |
| **M06** | ۶ — فرانت‌اند | MP Studio (Electron+React+Zustand) + MP Client (Flutter+Riverpod+drift) | `planner` → `tdd-guide` → `build-error-resolver` |
| **M07** | ۷ — دیزاین سیستم | design tokens + shadcn/Tailwind + flutter_animate + RTL فارسی + Vazirmatn | `architect` → `code-reviewer` |
| **M08** | ۸ — احراز هویت | OTP + JWT + RBAC (casbin) + «خروج از همه دستگاه‌ها» | `tdd-guide` → `security-reviewer` → `build-error-resolver` |
| **M09** | ۹ — امنیت | OWASP checklist + هدرها + audit log + رضایت‌نامه بیومتریک + رمزنگاری FaceTemplate | `security-reviewer` → `code-reviewer` |
| **M10** | ۱۰ — CI/CD | GitHub Actions (lint→test→build→scan→deploy) + Dokploy + feature flags | `architect` → `build-error-resolver` |
| **M11** | ۱۱ — زیرساخت | Docker-compose (FastAPI+Valkey+Ollama+Caddy) + Ansible | `architect` → `e2e-runner` |
| **M12** | ۱۲ — کش/کارایی | Valkey cache + invalidation + فشرده‌سازی ffmpeg + lazy loading | `tdd-guide` → `code-reviewer` |
| **M13** | ۱۳ — مانیتورینگ | Prometheus+Grafana+GlitchTip + SLO «گیت < ۲ ثانیه» + runbook | `architect` → `doc-updater` |
| **M14** | ۱۴ — تست کامل | هرم تست: pytest/Vitest/flutter_test + Playwright E2E + k6 (بار گیت) | `tdd-guide` → `e2e-runner` → `build-error-resolver` |
| **M15** | ۱۵ — AI محصول | موتور قواعد (ACSM/NSCA) + Ollama (فقط توضیح) + n8n + تأیید مربی | `planner` → `tdd-guide` → `security-reviewer` |
| **M16** | ۱۶ — مستندات | README/CONTRIBUTING/Changelog/Mermaid/runbooks | `doc-updater` → `code-reviewer` |
| **M17** | یکپارچگی نهایی | E2E کامل + اسکن امنیت نهایی + `finn/FINAL_REPORT.md` + release | `e2e-runner` → `security-reviewer` → `doc-updater` |

> **موازی‌سازی اختیاری:** پس از سبزشدن M03، چرخه‌های مستقل (مثلاً M07 و M08) را می‌توان با چند ایجنت موازی (git worktree) پیش برد؛ ابزار ارکستراسیون **Ruflo** (تأییدشده در پیوست ب طرح) قابل افزودن است. حالت پیش‌فرض همان ترتیبی است.

---

## ۷. کارت میکرو-چرخه‌ها (هدف، ورودی، خروجی، دام‌ها)

### M00 — بوت‌استراپ
- **هدف:** فاز ۰ (نصب ECC) + ساخت `mp-app/` + `docs/MuscleParadise/` + راه‌اندازی git و CI سبک.
- **ورودی:** همین سند + طرح ۱۶ لایه.
- **خروجی:** محیط آماده، اسکلپ پوشه‌ها، اولین commit.
- **گیت:** چک‌لیست فاز ۰ (بخش ۳.۵) همه ✓.
- **دام طرح:** نصب نشدن کامل ECC → چرخه شروع نمی‌شود.

### M01 — PRD
- **هدف:** User Story برای عضو/مربی/پذیرش/مدیر + معیار پذیرش Given/When/Then + جداسازی MVP (F1–F3) از Full (F4–F7) + شاخص‌های موفقیت.
- **گیت‌ها:** هر story معیار پذیرش دارد؛ مفاهیم مبهم (مثل «شخصی‌سازی خوب») به زنجیرهٔ ورودی→موتور→خروجی→تأیید مربی تبدیل شده‌اند.
- **دام طرح:** نیازمندی مبهم بدون زنجیرهٔ عملیاتی.

### M02 — معماری
- **هدف:** مونولیت ماژولار (نه میکروسرویس)، C4 متنی، ADR-001 تا ADR-004 (SQLite→Postgres مسیر مهاجرت، موتور قواعد، YuNet/SFace به‌خاطر لایسنس).
- **گیت‌ها:** هر ADR وضعیت «پذیرفته» دارد؛ مرز ماژول‌ها در `mp-app/backend/modules/` مشخص است.
- **دام طرح:** وسوسهٔ میکروسرویس «چون بزرگ‌ها این‌کار را می‌کنند».

### M03 — دیتابیس
- **هدف:** SQLAlchemy 2.x + Alembic؛ موجودیت‌های ERD طرح (Member/Membership/Payment/Assessment14Domain/DomainScore/JacksonPollock/FaceTemplate/CheckIn/WorkoutProgram/…) + `branch_id` در همهٔ جدول‌های اصلی از روز اول + ایندکس‌ها + رمزنگاری embedding چهره (PyNaCl).
- **گیت‌ها:** migrationها از صفر تا آخر روی دیتابیس تمیز اجرا می‌شوند؛ تست بازیابی بکاپ (restic) مستند شده.
- **دام طرح:** فراموشی `branch_id` و دردسر مهاجرت بعدی.

### M04 — قرارداد API
- **هدف:** REST نسخه‌دار `/api/v1/`، OpenAPI خودکار، `slowapi` روی OTP/لاگین.
- **گیت‌ها:** اسکیمای Pydantic برای همه endpointها؛ مستند Swagger کامل.
- **دام طرح:** شروع بدون نسخه‌بندی API.

### M05 — بک‌اند هسته
- **هدف:** Router→Service→Repository؛ ماژول‌های membership, assessment, programs, payments, face_id, notification؛ APScheduler برای یادآوری تمدید و چرخهٔ بازآزمایی ۶–۸ هفته؛ structlog.
- **گیت‌ها:** پوشش ≥ ۷۰٪؛ منطق تجاری فقط در service (نه router).
- **دام طرح:** controller فربه (منطق داخل router).

### M06 — فرانت‌اند
- **هدف:** MP Studio (Electron+React+Vite+Zustand) و MP Client (Flutter+Riverpod+go_router+drift برای حالت آفلاین).
- **گیت‌ها:** RTL کامل فارسی؛ حالت تاریک default؛ کنتراست رنگ برند (زمرد/طلایی روی #0B0F14) چک‌شده.
- **دام طرح:** تلاش برای استفاده از کتابخانه‌های React داخل Flutter.

### M07 — دیزاین سیستم
- **هدف:** design tokens مشترک (JSON) بین React و Flutter؛ shadcn/ui **یا** DaisyUI (هرگز هر دو)؛ Framer Motion + flutter_animate.
- **گیت‌ها:** فقط یک سیستم کامپوننت React انتخاب شده؛ تایپوگرافی Vazirmatn subset شده.
- **دام طرح:** قاطی‌کردن چند سیستم کامپوننت.

### M08 — احراز هویت
- **هدف:** fastapi-users + pyotp + python-casbin + JWT access/refresh با ابطال؛ «خروج از همهٔ دستگاه‌ها».
- **گیت‌ها:** OTP/رمز فقط هش‌شده در دیتابیس؛ تست نفوذ سطحی روی auth سبز.
- **دام طرح:** ذخیرهٔ خام OTP.

### M09 — امنیت
- **هدف:** چک‌لیست OWASP هر endpoint؛ هدرها در Caddy؛ `.env` رمزنگاری‌شده؛ audit log عملیات حساس؛ سیاست دادهٔ بیومتریک (رضایت، حداقل‌سازی، حق حذف).
- **گیت‌ها:** Strix فقط روی staging با دادهٔ مصنوعی؛ `pip-audit`/`npm audit` بدون بحرانی جدید.
- **دام طرح:** اجرای پنتست LLM-محور روی دادهٔ واقعی اعضا.

### M10 — CI/CD
- **هدف:** GitHub Actions: lint→test→build→scan→deploy؛ Dokploy با rollback به ایمیج قبلی؛ feature_flags ساده در دیتابیس.
- **گیت‌ها:** pipeline سبز روی main؛ rollback تست‌شده.
- **دام طرح:** پیچیده‌کردن pipeline با ابزار Kubernetes-محور.

### M11 — زیرساخت
- **هدف:** docker-compose (FastAPI+SQLite/Postgres+Ollama مدل کوانتیزه+Caddy)؛ Ansible به‌جای Terraform؛ فایل استاتیک از هاست داخلی با فشرده‌سازی ffmpeg.
- **گیت‌ها:** بالاآمدن کامل استک با یک دستور؛ مستند provisioning.
- **دام طرح:** Terraform provider ابر خارجی روی زیرساخت ایرانی.

### M12 — کش و کارایی
- **هدف:** Valkey (نه Redis جدید — لایسنس) برای لیست‌های پرتکرار با invalidation درست؛ lazy loading در Flutter.
- **گیت‌ها:** تست invalidation (کش قدیمی نمایش داده نشود)؛ بودجهٔ عملکرد حفظ شود.
- **دام طرح:** کش دادهٔ کاربرمحور بدون invalidation.

### M13 — مانیتورینگ
- **هدف:** Prometheus+Grafana+GlitchTip؛ آلارم (نه فقط داشبورد!)؛ health-check هر ۵ دقیقه با ntfy/pیامک؛ SLO «۹۹٪ درخواست‌های گیت < ۲ ثانیه»؛ runbook.
- **گیت‌ها:** یک سناریوی خرابی شبیه‌سازی و آلارم آتش می‌گیرد.
- **دام طرح:** داشبورد زیبا بدون آلارم.

### M14 — تست کامل
- **هدف:** هرم تست طرح (واحد زیاد، یکپارچگی متوسط، E2E کم ولی روی مسیرهای حیاتی «ثبت‌نام→پرداخت→چک‌این» و «تأیید برنامه توسط مربی»)؛ k6 برای هم‌زمانی گیت در ساعت شلوغی؛ Playwright روی Electron؛ `flutter_test`+`integration_test`.
- **گیت‌ها:** E2E مسیرهای حیاتی سبز؛ بودجهٔ پوشش حفظ.
- **دام طرح:** فقط E2E شکننده بدون تست واحد.

### M15 — AI محصول
- **هدف:** موتور قواعد قطعی (تصمیم‌گیرندهٔ بار تمرین) + Ollama فقط برای توضیح/انگیزش + n8n برای اتوماسیون + الزام تأیید مربی + ارزیابی مدل با ۱۰ ورودی نمونه پس از هر آپدیت.
- **گیت‌ها:** هیچ مسیری LLM را بدون عبور از موتور قواعد به عدد نمی‌رساند (G8)؛ تست ۱۰ نمونه‌ای پایدار.
- **دام طرح:** تغییر مستقیم اعداد بار توسط LLM.

### M16 — مستندات
- **هدف:** README، CONTRIBUTING، Changelog (Keep a Changelog)، دیاگرام‌های Mermaid، runbookها، راهنمای onboarding.
- **گیت‌ها:** هر PR مهم خطی به Changelog افزوده؛ مستندات با کد همگام.
- **دام طرح:** مستندات یک‌باره و رهاشده.

### M17 — یکپارچگی نهایی
- **هدف:** اجرای کامل همه تست‌ها + E2E + اسکن امنیت نهایی + تست بار + تولید `finn/FINAL_REPORT.md` (شواهد: خروجی تست‌ها، درصد پوشش، نتایج اسکن، فهرست ADRها، وضعیت LEDGER) + آماده‌سازی release.
- **گیت‌ها:** هیچ گیت قرمزی در هیچ لایه‌ای باقی نمانده؛ همهٔ آیتم‌های LEDGER بسته یا مستند شده‌اند.

---

## ۸. پروتکل دیباگ و شکست (در هر مرحله)

```
خطا/شکست تست
  │
  ├─ تلاش ۱: build-error-resolver → رفع → اجرای کامل تست‌ها
  │     ├─ سبز؟ → ثبت در LEDGER (اگر درس جدیدی داشت) → ادامه
  │     └─ قرمز؟ ↓
  ├─ تلاش ۲: بازتولید خطا (minimal repro) → ریشه‌یابی → رفع → تست + رگریشن جدید
  │     ├─ سبز؟ → ادامه
  │     └─ قرمز؟ ↓
  ├─ تلاش ۳: محدودکردن دامنه (کوچک‌ترین زیربخش) → رفع → تست
  │     ├─ سبز؟ → ادامه
  │     └─ قرمز؟ ↓
  └─ بعد از ۳ شکست: ROLLBACK میکرو-چرخه (git reset به آخرین کامیت سبز)
        → ثبت کامل ماجرا در LEDGER + DECISIONS
        → planner: بازطراحی رویکرد (نه تکرار همان روش با کد جدید)
        → از سرگیری چرخه با رویکرد جدید (شمارنده تلاش صفر می‌شود؛ فقط یک بار در هر چرخه)
```

- هر خطا در `LEDGER.md` با ستون «قانون جدید (هرگز…)» ثبت می‌شود.
- خطاهای محیطی (قطع شبکه، سرویس در دسترس نیست): ۳ بار تلاش مجدد با تأخیر، سپس مسیر جایگزین طرح (جدول پیوست الف) و ثبت تصمیم.

---

## ۹. موتور ضدتکرار (Anti-Repetition Engine)

1. **پیش از ساخت:** Grep/Glob برای نام‌ها و مفاهیم مشابه؛ اگر ماژول/تابع مشابهی هست، افزونه بساز، کپی نکن.
2. **پیش از رفع باگ:** جست‌وجوی LEDGER برای باگ مشابه قبلی — اگر هست، «قانون هرگز» همان را اعمال کن.
3. **پس از رفع باگ:** تست رگریشن در `REGRESSIONS.md` + اجرایش در همهٔ چرخه‌های بعد.
4. **درس تکراری ممنوع:** اگر همان درس دوباره ثبت شد، یعنی لوپ خطا کرده → چرخه قبول نیست تا یک «قانون اجرایی» (مثلاً تست، هوک، یا lint rule) آن را مکانیکی کند — نه فقط تذکر متنی.
5. **کامیت‌ها:** هر commit فقط مربوط به یک چرخه؛ تاریخچه تمیز = قابلیت rollback واقعی.

---

## ۱۰. استاندارد «کلاس جهانی» (تعریف عملیاتی کیفیت ایده‌آل)

| بُعد | معیار سنجش‌پذیر |
|------|------------------|
| درستی | همهٔ تست‌ها سبز؛ معیارهای پذیرش Given/When/Then هر story برآورده |
| پایداری | پوشش ≥ ۷۰٪ بدون روند نزولی؛ تست‌های رگریشن همیشه سبز |
| امنیت | OWASP checklist هر endpoint؛ bandit/pip-audit/npm audit تمیز؛ دادهٔ بیومتریک رمزنگاری‌شده؛ audit log |
| کارایی | SLO گیت < ۲ ثانیه (۹۹٪)؛ تست بار k6 بدون فروپاشی در بار شبیه‌سازی‌شده |
| تجربه کاربری | RTL کامل فارسی، Vazirmatn، حالت تاریک، کنتراست WCAG، آفلاین برنامهٔ امروز |
| مهندسی | لینت/فرمت صفرخطا؛ بدون کد مرده/تکراری (گزارش refactor-cleaner)؛ ADR برای هر تصمیم |
| مستندات | README/CHANGELOG/API docs/runbook همگام با کد (گزارش doc-updater) |
| بازتولیدپذیری | نصب ECC با کامیت پین‌شده؛ migration از صفر؛ استک با یک دستور بالا می‌آید |

---

## ۱۱. شرایط پایان (Stop Conditions)

**پایان موفق:** M00 تا M17 همگی Done با همهٔ گیت‌های بخش ۵ + `finn/FINAL_REPORT.md` شامل شواهد + LEDGER بدون آیتم باز بحرانی.

**پایان اضطراری (فقط در این دو حالت):**
1. مانع خارج از کنترل محیط (مثلاً دسترسی شبکه به مخزن لازم) که پس از ۳ تلاش + مسیر جایگزین حل نشود → گزارش دقیق وضعیت + محل توقف تمیز.
2. تناقض بنیادین بین دو سند ورودی که با ADR قابل حل نباشد → ثبت در DECISIONS + انتخاب محافظه‌کارانه‌ترین گزینه + ادامه (این حالت نیز «توقف» نیست، فقط اطلاع‌رسانی در گزارش نهایی).

هیچ حالت دیگری مجوز توقف یا پرسیدن سؤال از انسان را نمی‌دهد.

---

## ۱۲. پرامپت آغاز (Kickoff — همین متن را به ایجنت بده)

```
سند docs/MuscleParadise/FINN_LOOP.md را به‌عنوان پروتکل اجرای خودکار بپذیر و اجرا کن.
۱) فاز ۰ را اجرا کن: bash docs/MuscleParadise/finn/install-ecc.sh و چک‌لیست ۳.۵ را تأیید کن.
۲) میکرو-چرخه‌های M00 تا M17 را «پشت سر هم» و بدون توقف انسانی اجرا کن؛ در هر گام ایجنت ECC مشخص‌شده در جدول بخش ۶ را فراخوانی کن.
۳) قوانین طلایی G1 تا G10، پروتکل دیباگ بخش ۸ و موتور ضدتکرار بخش ۹ را رعایت کن.
۴) کیفیت هر چرخه باید همهٔ گیت‌های بخش ۵ و استاندارد بخش ۱۰ را پاس کند.
۵) در پایان finn/FINAL_REPORT.md را با شواهد تولید کن. تا پایان موفق یا شرایط بخش ۱۱ متوقف نشو و سؤال نپرس.
```

---

## ۱۳. پیوست — مرجع ایجنت‌های ECC

| ایجنت | نقش | فازهای FINN که فراخوانی می‌شود |
|-------|------|--------------------------------|
| `planner` | تحلیل نیازمندی و برنامهٔ اجرایی گام‌به‌گام | Forge |
| `architect` | تصمیم‌های معماری و طراحی سیستم | Forge |
| `tdd-guide` | روش‌شناسی تست‌محور (تست قبل از کد) | Forge |
| `build-error-resolver` | رفع خطاهای build و تست | Forge / Normalize |
| `code-reviewer` | بازبینی کیفیت و امنیت کد | Inspect |
| `e2e-runner` | تست‌های End-to-End (Playwright) | Inspect |
| `refactor-cleaner` | حذف کد مرده/تکراری، بهسازی ساختار | Normalize |
| `security-reviewer` | تحلیل آسیب‌پذیری (OWASP) | Normalize |
| `doc-updater` | همگام‌سازی مستندات با کد | Next |

**فرمان‌های مفید:** `/plan` (شروع هر Forge)، `/tdd` (تست‌محور)، `/code-review` (Inspect)، `/e2e` (Inspect).
**اسکیل‌های مفید:** `verification-loop` و `eval-harness` (حلقهٔ تأیید)، `security-review` (چک‌لیست امنیت)، `tdd-workflow`، `backend-patterns`، `coding-standards`، `continuous-learning` (استخراج خودکار درس‌ها برای LEDGER).

> یادداشت اعتبارسنجی: ECC در تاریخ ۲۰۲۶-۱۱-۱۴ واقعی و نصب‌شدنی تأیید شد (کامیت `432485ba` در فاز ۰ این سند). این یادداشت پیوست «ب» طرح ۱۶ لایه (ابزارهای تأییدنشده) را دربارهٔ ECC و Finn-loop می‌بندد.
