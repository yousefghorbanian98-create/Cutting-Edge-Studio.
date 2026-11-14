#!/usr/bin/env bash
# ============================================================
# FINN Loop — Phase 0 (الزامی): نصب ECC در فضای کاری
# Everything Claude Code (ECC) — github.com/WorldFlowAI/everything-claude-code
# این اسکریپت را هر ایجنت هوش مصنوعی «قبل» از شروع لوپ اجرا می‌کند.
# ============================================================
set -euo pipefail

ECC_REPO="${ECC_REPO:-https://github.com/WorldFlowAI/everything-claude-code.git}"
ECC_REF="${ECC_REF:-main}"

# ریشهٔ مخزن: این فایل در docs/MuscleParadise/finn/ قرار دارد
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
FINN_DIR="$ROOT/.finn"
ECC_DIR="$FINN_DIR/ecc"
CLAUDE_DIR="$ROOT/.claude"

echo "[FINN/Phase-0] ریشهٔ کاری: $ROOT"

# --- 1/5 دریافت ECC (کلون یا به‌روزرسانی، با ثبت کامیت برای بازتولیدپذیری) ---
echo "[FINN/Phase-0] 1/5 دریافت ECC از $ECC_REPO@$ECC_REF ..."
if [ -d "$ECC_DIR/.git" ]; then
  git -C "$ECC_DIR" fetch --depth 1 origin "$ECC_REF"
  git -C "$ECC_DIR" checkout -q FETCH_HEAD
else
  git clone --depth 1 --branch "$ECC_REF" "$ECC_REPO" "$ECC_DIR"
fi
ECC_COMMIT="$(git -C "$ECC_DIR" rev-parse HEAD)"
echo "$ECC_COMMIT" > "$FINN_DIR/ecc-commit.txt"
echo "      کامیت ECC: $ECC_COMMIT"

# --- 2/5 نصب مؤلفه‌ها در .claude/ (agents, commands, skills, rules, hooks) ---
echo "[FINN/Phase-0] 2/5 نصب مؤلفه‌ها در .claude/ ..."
mkdir -p "$CLAUDE_DIR"
for part in agents commands skills rules hooks; do
  if [ -d "$ECC_DIR/$part" ]; then
    rm -rf "${CLAUDE_DIR:?}/$part"
    cp -R "$ECC_DIR/$part" "$CLAUDE_DIR/$part"
    echo "      نصب شد: $part"
  fi
done

# --- 3/5 راه‌اندازی فایل‌های وضعیت لوپ (بدون بازنویسی وضعیت موجود) ---
echo "[FINN/Phase-0] 3/5 راه‌اندازی فایل‌های وضعیت لوپ ..."
mkdir -p "$FINN_DIR/state"
if [ ! -f "$FINN_DIR/state/LEDGER.md" ]; then
  cat > "$FINN_DIR/state/LEDGER.md" <<'EOF'
# FINN Ledger — درس‌ها، باگ‌ها و قوانین «هرگز تکرار نشود»
> هر ایجنت در آغاز «هر» میکرو-چرخه این فایل را کامل می‌خواند. هیچ خطی حذف نمی‌شود؛ فقط اضافه می‌شود.

| # | تاریخ | چرخه | نوع (باگ/درس/تصمیم) | شرح | قانون جدید (هرگز...) | تست رگریشن |
|---|-------|------|----------------------|------|----------------------|-------------|
EOF
fi
if [ ! -f "$FINN_DIR/state/STATE.md" ]; then
  cat > "$FINN_DIR/state/STATE.md" <<'EOF'
# FINN State — وضعیت جاری لوپ
- وضعیت: INIT (پس از Phase-0 آماده)
- میکرو-چرخه جاری: —
- شمارنده تلاش‌های رفع خطا در چرخه جاری: 0
- آخرین گیت سبز: —
EOF
fi
if [ ! -f "$FINN_DIR/state/DECISIONS.md" ]; then
  cat > "$FINN_DIR/state/DECISIONS.md" <<'EOF'
# FINN Decisions — ثبت تصمیم‌های خودمختار (ADR سبک)
> هرگاه لوپ بدون نظارت انسان تصمیمی گرفت، اینجا ثبت می‌کند: زمینه، گزینه‌ها، انتخاب، دلیل.
EOF
fi
if [ ! -f "$FINN_DIR/state/REGRESSIONS.md" ]; then
  cat > "$FINN_DIR/state/REGRESSIONS.md" <<'EOF'
# FINN Regressions — رجیستری تست‌های رگریشن
> هر باگ رفع‌شده = حداقل یک تست رگریشن اینجا ثبت و در همهٔ چرخه‌های بعدی اجرا می‌شود.
| شناسه تست | مسیر فایل تست | باگ مرتبط | تاریخ افزودن | وضعیت |
|-----------|----------------|-----------|---------------|--------|
EOF
fi

# --- 4/5 تأیید وجود ۹ ایجنت ECC ---
echo "[FINN/Phase-0] 4/5 تأیید ایجنت‌ها ..."
MISSING=0
for a in planner architect tdd-guide code-reviewer security-reviewer build-error-resolver e2e-runner refactor-cleaner doc-updater; do
  if [ -f "$CLAUDE_DIR/agents/$a.md" ]; then
    echo "      ✓ $a"
  else
    echo "      ✗ MISSING: $a"
    MISSING=1
  fi
done
if [ "$MISSING" -ne 0 ]; then
  echo "[FINN/Phase-0] خطا: همهٔ ایجنت‌ها نصب نشدند." >&2
  exit 1
fi

# --- 5/5 گزارش نهایی ---
cat <<EOF
[FINN/Phase-0] 5/5 ✓ نصب ECC کامل شد.
      کامیت:   $ECC_COMMIT
      ایجنت‌ها: $CLAUDE_DIR/agents/
      وضعیت:   $FINN_DIR/state/
اکنون می‌توانید میکرو-چرخهٔ M01 را آغاز کنید (به FINN_LOOP.md مراجعه کنید).
EOF
