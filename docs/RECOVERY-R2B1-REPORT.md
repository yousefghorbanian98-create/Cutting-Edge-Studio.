# Evidence Report — R2b1 OSS rhythm adapter and inference guards

Date: **2026-11-04** · Branch `arena/dbb53bc2-cutting-edge-studio` · PR **#1** · Code **`d1decc2`**

## نتیجه / Verdict

**ادامهٔ R2 با اولویت اجزای آماده:** آداپتر آزمایشی ضرب‌آهنگ، مستقیماً از
`librosa.beat.beat_track` با مجوز ISC استفاده می‌کند؛ الگوریتم تشخیص ضرب‌آهنگ از صفر نوشته نشده است.
تست واقعی روی دو صدای کلیکِ تولیدشده با خود librosa و یک سکوت اجرا شد؛ دسترسی شبکه در زمان
اندازه‌گیری مسدود بود. توابع آمادهٔ NumPy/SciPy نیز جای پیاده‌سازی دستی سه helper عددی را گرفتند.

**این هنوز قابلیت متصل به رابط کاربری نیست.** آداپتر فقط WAV محلی استاندارد را دریافت می‌کند؛
اتصال به job محدودشده، استخراج صوت با FFmpeg و گزارش پروژه/رابط کاربری در **R2b2** باقی است.
هیچ تحلیل مدل، StyleDNA، EDL یا آماده‌بودن نصب‌کننده ادعا نمی‌شود. **Release: BLOCKED.**

**Step 260/260 = 100% historical authored steps**, unchanged. **R2b1 synthetic rhythm fixtures: 3/3 passed.**
These figures are not release readiness, music-quality acceptance, or full R2 completion.

## 1. Reuse and alternative decisions

The Owner authorized continuing the existing path while preferring ready free/licence-compatible OSS components and examining alternatives before adding custom code. This does not retroactively claim every previous implementation came from n8n or upstream projects.

| Need | Selected existing component | Local changes / limits |
|---|---|---|
| Beat/tempo estimation | **librosa 0.11.0**, ISC; [`librosa/librosa`](https://github.com/librosa/librosa/tree/0.11.0) | Calls its existing dynamic-programming tracker. Glue validates PCM input, records provenance and surfaces errors. No training, new beat detector, supplied labels or custom WAV parser. [Unmodified notice](../licenses/LIBROSA-ISC.md) |
| PCM reading | Python `wave` standard library + NumPy conversion | Only mono signed 16-bit PCM, 22,050 Hz, 1–600 s; invalid/truncated/changed files fail. No silent truncation or homemade resampling. Future FFmpeg job supplies this format. |
| Normalize/cosine/softmax helpers | NumPy + `scipy.linalg.norm`, `scipy.spatial.distance.cosine`, `scipy.special.softmax` | Replaced hand-written numerical implementations; existing zero/empty/mismatched-input behavior and temperature interface retained. These are helpers, not proof of model inference. |
| Audio resampler dependency | Upstream Python-SoXR / libsoxr, LGPL-2.1-or-later | The initially resolved PyPI wheel had no external libsoxr dependency in `ldd`. It was replaced **before executing rhythm analysis** by an upstream source build using `USE_SYSTEM_LIBSOXR=ON`. `ldd` confirms a separate shared `libsoxr.so.0`. No library source algorithm was modified. |
| Alternative to that dependency for product audio conversion | Approved FFmpeg PCM conversion | Preferred future input path; librosa does not load media or resample in this adapter. Nevertheless its imported native dependencies still require audit. Do not assume the default PyPI wheel is approved for Windows distribution. |
| Workflow/orchestration | Existing application infrastructure retained | No new orchestration engine or n8n workflow is claimed in this patch. The synchronous adapter is **not** exposed as an unbounded API task. Next stage must reuse the existing cancellation/process boundary or another reviewed ready component. |

Optional librosa dependencies were provisioned on the development/test machine only. They were **not added to default `requirements.txt`** or enabled in the installer. Their complete Windows wheel/licence/native-linkage/packaging acceptance remains open. [Exploratory resolver selection](evidence/recovery-r2b1/experimental-dependencies.json) is **not** a production lock file or complete licence certificate.

## 2. Behavior and repairs

- New `backend/app/services/audio/rhythm.py` is a thin library adapter returning WAV SHA-256, sample count/duration, library version, estimated tempo and beat times with scope **audio-rhythm-only**. It does not identify sports actions or establish musical ground truth. Empty detections return **no beats and `tempo_bpm=None`**, not a default BPM.
- The adapter rejects invalid/non-finite/out-of-range estimator output and changed input files. Errors are logged and raised, not replaced with success. Missing optional librosa gives a build-machine provisioning error; the module performs no installation/download.
- Input is bounded to 600 s PCM, but **there is no independent cancellation/deadline boundary for librosa/Numba yet**. First-call JIT can be slow. This is why it is not mounted on an API thread or advertised as a working wizard stage.
- `InferenceRegistry.load()` now rejects `None` from placeholder loaders; it can no longer record `inference.loaded` for unwired default specs. This does not wire those models or verify their weights.
- The resident-count policy now refuses a lower-priority load when higher-priority residents occupy the configured limit. Previously it could keep the existing handle and add another beyond that limit. Tests verify the rejected loader is never called. This is a registry-count guard, not a measured physical RAM/VRAM guarantee.
- A directory can no longer masquerade as a local model file (`is_file`, not merely `exists`).
- Package metadata now uses **setuptools' built-in dynamic dependency-file support** to read the audited `requirements.txt`, rather than maintaining a second stale list of pins in `pyproject.toml`. A real wheel build confirmed its runtime requirements contain current pins and do not add librosa/soxr. The wheel is not a Windows sidecar/installer acceptance result.
- A full local Python-environment audit found existing development dependency **pytest 8.3.4** affected by **PYSEC-2026-1845 / GHSA-6w46-j5rx-g56g**. Upgraded to **pytest 9.0.3** and compatible **pytest-asyncio 1.4.1.post1**; both test modes pass. The subsequent Python-environment audit reports no known advisories. This does not audit native binaries, operating-system libraries or all frontend dependencies.

## 3. Actual measurements and tests

Owned stimuli are generated by `librosa.clicks`, written as PCM by Python `wave`, and removed after the run. They are not bundled third-party media. [`scripts/local-tests/audio-rhythm.py`](../scripts/local-tests/audio-rhythm.py) calls the real adapter with network connections denied.

| Stimulus | Actual library estimate | Detected beats | Interpretation |
|---|---:|---:|---|
| 12 s click track, nominal 90 BPM | **89.10290948275862 BPM** | **17** | Estimated, not exact ground truth |
| 12 s click track, nominal 120 BPM | **117.45383522727273 BPM** | **21** | Estimated, not exact ground truth |
| 12 s digital silence | **None** | **0** | No fabricated default tempo |

Each measurement analyzed **264,600 samples**. WAV hashes were independently recomputed. Full outputs: [JSON](evidence/recovery-r2b1/real-rhythm-results.json), [run log](evidence/recovery-r2b1/real-rhythm-run.txt).

| Gate | Observed result | Evidence |
|---|---|---|
| Backend lint/format | Passed, **82 files** | [backend-lint.txt](evidence/recovery-r2b1/backend-lint.txt) |
| Full suite with optional real analysis enabled | **227 passed**, coverage **94.86%** | [backend-tests-analysis.txt](evidence/recovery-r2b1/backend-tests-analysis.txt) |
| Default/base suite | **224 passed, 3 skipped**; skips are explicitly opt-in real-librosa cases | [backend-tests-base.txt](evidence/recovery-r2b1/backend-tests-base.txt) |
| Frontend lint/tests | Passed; **154 tests / 20 files** | [lint](evidence/recovery-r2b1/frontend-lint.txt), [tests](evidence/recovery-r2b1/frontend-tests.txt) |
| TypeScript/Vite production build | Passed, **2,189 modules**, main chunk **286.47 kB / 89.67 kB gzip** | [frontend-build.txt](evidence/recovery-r2b1/frontend-build.txt) |
| Python wheel build + metadata | Passed; requirements come from current default file | [build](evidence/recovery-r2b1/backend-wheel.txt), [Requires-Dist](evidence/recovery-r2b1/wheel-requirements.txt) |
| Full local Python environment audit after dev-tool fix | **No known vulnerabilities found** by pip-audit/PyPI; not a native-code or licence audit | [audit JSON](evidence/recovery-r2b1/experimental-environment-audit.json) |
| New browser/model/Windows runtime acceptance | **NOT CLAIMED** | No new UI/API feature was exposed; full R2 remains open |

Actual excerpts:

```text
$ ruff check app tests && ruff format --check app tests
All checks passed!
82 files already formatted
$ CE_ANALYSIS_TESTS=1 python -m pytest --cov=app --cov-report=term-missing
Required test coverage of 80.0% reached. Total coverage: 94.86%
227 passed in 14.94s
$ python -m pytest
224 passed, 3 skipped in 6.08s
$ npm test
Test Files  20 passed (20)
Tests       154 passed (154)
$ npm run build
✓ built in 4.77s
```

Existing non-fatal React/Radix and Vite annotation/empty-chunk warnings remain in raw output. Setuptools reports the existing TOML licence-table deprecation during wheel creation; the build still succeeds. UI source was not changed in this patch: the [previous actual R2a screenshot](evidence/recovery-r2a/03-measured-result-models-blocked.png) shows the **unchanged** decode-only interface, not an audio-rhythm UI. Prior R2a 26/26 browser results are historical and were not rerun/relabelled as R2b1 acceptance.

## 4. Optional environment provenance / reproduction

- Upstream SoXR **1.1.0 source sdist**, SHA-256 **`9f228ae21c78fa9359ca98d8a5e8e91f30639e438e574133dace62c5b5309e44`**, was fetched at build/test provisioning time from PyPI, not at application runtime.
- Built bundled upstream libsoxr source as a **shared** library using CMake `BUILD_SHARED_LIBS=ON`, then built the upstream Python extension with `USE_SYSTEM_LIBSOXR=ON`, `SOXR_LIBRARY`/`SOXR_INCLUDE_DIR` pointing to that library and an explicit local test RPATH. No custom DSP code or library algorithm patch was introduced.
- This sandbox lacked Python development headers. Matching CPython **v3.11.2** source was fetched from GitHub and configured to provide development headers for the test extension build. These are external provisioning artifacts, not committed product code. Initial builds failed for missing `setuptools_scm` and then missing headers; installing the build dependency and supplying the matching headers resolved them.
- [Dynamic linkage + native binary hashes](evidence/recovery-r2b1/soxr-dynamic-linkage.txt) prove the tested extension resolves `/tmp/ce-r2b-audio/lib/libsoxr.so.0`. These Linux test paths must not be copied into a Windows installer or treated as a portable deployment recipe.
- Normal CI intentionally does **not** acquire/enable the optional analysis environment. Do not blindly install/bundle the resolver-selected PyPI wheels; audit the target-platform dependency graph and dynamic linkage first.

After separately provisioning the audited optional environment:

```sh
cd backend
CE_ANALYSIS_TESTS=1 .venv/bin/python -m pytest --cov=app --cov-report=term-missing
PYTHONPATH=. .venv/bin/python ../scripts/local-tests/audio-rhythm.py
.venv/bin/python -m pip_audit --strict --progress-spinner off
```

No runtime downloads, training, fine-tuning, unapproved H.264 encoder calls, telemetry or user-media uploads were added. Native/Windows distribution acceptance is **still pending**.

## 5. CI repairs, without claiming a new green installer

Previous push CI **41899645032** passed Linux backend/frontend/security but failed Windows NSIS. The earlier frontend-path repair worked far enough to reach installer generation; annotations now identify the next concrete failure: **`Persian.nlf` not found**. Upstream NSIS supplies **`Farsi.nlf`**, not `Persian.nlf`; the configuration now retains `English` and changes the internal Persian-language identifier to `Farsi`. A guard test covers the configuration. This is **not** proof of a successful new Windows build.

Sources: [installer annotations](evidence/recovery-r2b1/installer-annotations.json), [upstream Farsi language-file identity](evidence/recovery-r2b1/nsis-farsi-source.json), [previous push jobs](evidence/recovery-r2b1/previous-ci.json).

Previous PR CI **41899652618** separately failed its gitleaks action when attempting to write PR comments with insufficient token permissions. [Annotations](evidence/recovery-r2b1/pr-security-annotations.json) show `Resource not accessible by integration`. PR comments are now disabled via the action's documented `GITLEAKS_ENABLE_COMMENTS=false`, retaining scanning, summaries/artifacts and least privilege. **This does not suppress secret findings or certify that the PR has no findings**; the fresh scan must be evaluated independently. No secret allowlist was broadened and no scanner was disabled.

## 6. Git and next gate

[`git log --oneline -5`](evidence/recovery-r2b1/git-log.txt), [`git diff --stat d941d87..d1decc2`](evidence/recovery-r2b1/git-diff-stat.txt): **13 files changed, 423 insertions, 31 deletions**. Documentation/evidence is committed separately on the same fixed branch; PR #1 remains open for the Owner.

Next **R2b2**: integrate audio extraction and this ready-library adapter into an isolated, cancellable/time-limited project job; bind results to the original asset hashes; persist real results; expose honest rhythm-only scope in the existing UI. Only then may the application advertise a working beat-analysis operation. Real music, no-audio inputs and failure/restart/browser acceptance are required. Pose/action/shot/StyleDNA/EDL and approved full offline Windows packaging remain separate unfinished gates.
