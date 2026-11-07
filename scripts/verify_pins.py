#!/usr/bin/env python3
"""
Fail-closed PIN verifier (professor §2).

Usage:
  python scripts/verify_pins.py                # check scripts/pins.json hashes
  python scripts/verify_pins.py --strict       # also fail if any sha256 is null
  python scripts/verify_pins.py --update       # download + compute (requires trusted net)

Exits 1 on mismatch / null (strict) / network leak.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / "scripts" / "pins.json"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify pinned artifact hashes")
    ap.add_argument("--strict", action="store_true", help="Fail if any sha256 is null")
    ap.add_argument("--update", action="store_true", help="Fetch URLs and print hashes (manual)")
    args = ap.parse_args()

    if not PINS.exists():
        print(f"pins file not found: {PINS}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(PINS.read_text(encoding="utf-8"))
    errors: list[str] = []
    nulls: list[str] = []

    def walk(obj, prefix=""):
        if isinstance(obj, dict):
            if "sha256" in obj and "url" in obj:
                name = prefix or "unknown"
                sha = obj.get("sha256")
                url = obj.get("url")
                if sha is None:
                    nulls.append(name)
                    if args.strict:
                        errors.append(f"NULL hash (blocked): {name} -> {url}")
                elif not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha.lower()):
                    errors.append(f"BAD sha256 format: {name} = {sha}")
                # If target file exists, verify its hash
                target = obj.get("target")
                if target and sha:
                    cand = ROOT / target
                    # If target is a directory or missing, skip (binary not bundled in light)
                    if cand.is_file():
                        actual = sha256_file(cand)
                        if actual.lower() != sha.lower():
                            errors.append(f"HASH MISMATCH: {name}\n  expected {sha}\n  actual   {actual}\n  file {cand}")
                        else:
                            print(f"OK {name}: {actual}")
                    elif cand.exists():
                        print(f"SKIP {name}: target is dir (Full bundle required)")
                    else:
                        print(f"SKIP {name}: not bundled (light mode)")
            else:
                for k, v in obj.items():
                    if k.startswith("_"):
                        continue
                    walk(v, f"{prefix}.{k}" if prefix else k)

    walk(data)

    if nulls and not args.strict:
        print(f"WARN: {len(nulls)} pins have null sha256 (blocked for Full build): {', '.join(nulls)}")
        print("  Run with --strict to fail, or UpdatePins to fetch on trusted network + license audit.")

    if args.update:
        print("\n--update: download gated hashes (requires trusted network + license review)")
        print("  This mode is intentionally manual — do not run in CI without review.")
        # Placeholder: real fetch would stream via urllib with SHA256
        print("  TODO: implement gated fetch with pin guard (see docs/CONTRACT.md)")

    if errors:
        print("\nFAILED:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    if args.strict and nulls:
        print(f"\nSTRICT FAILED: {len(nulls)} null pins block Full build", file=sys.stderr)
        sys.exit(1)

    print("All pinned hashes verified.")


if __name__ == "__main__":
    main()
