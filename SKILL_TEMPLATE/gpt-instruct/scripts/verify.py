#!/usr/bin/env python3
"""Verify gpt-instruct opencode skill installation."""
from pathlib import Path
import hashlib
import sys

def file_sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1024*1024), b""): h.update(c)
    return h.hexdigest()

SKILL = Path.home() / ".config" / "opencode" / "skills" / "gpt-instruct"
OPENCODE_CFG_CANDIDATES = [Path.home() / ".config" / "opencode" / "opencode.jsonc", Path.home() / ".config" / "opencode" / "opencode.json"]

def check():
    ok = True
    print("=== gpt-instruct opencode skill verify ===")
    # skill dir
    if not SKILL.exists():
        print(f"[FAIL] skill dir missing: {SKILL}")
        ok = False
    else:
        print(f"[OK] skill dir: {SKILL}")
        for req in ["SKILL.md", "prompts/gpt-5.6-sol-v45.md", "prompts/gpt-6-astra-v1.md", "src/opencode_instruct.py"]:
            p = SKILL / req
            if p.exists():
                print(f"  [OK] {req} ({p.stat().st_size} B, sha {file_sha256(p)[:12]})")
            else:
                print(f"  [FAIL] missing {req}")
                ok = False
    # opencode config
    cfg = next((c for c in OPENCODE_CFG_CANDIDATES if c.exists()), None)
    if cfg:
        print(f"[OK] opencode config: {cfg}")
        text = cfg.read_text(encoding="utf-8", errors="ignore")
        if "gpt-5.6-sol-v45" in text or "gpt-6-astra-v1" in text:
            print("  [INFO] prompt reference found in instructions")
        else:
            print("  [INFO] no prompt in instructions (skill trigger mode — normal)")
        if "gpt-instruct" in text:
            print("  [INFO] gpt-instruct mentioned")
    else:
        print("[WARN] opencode config not found")

    # codex check
    codex_cfg = Path.home() / ".codex" / "config.toml"
    if codex_cfg.exists():
        t = codex_cfg.read_text(encoding="utf-8", errors="ignore")
        if "gpt-5.6" in t or "gpt-6-astra" in t:
            print(f"[INFO] Codex config has prompt: {codex_cfg}")
        else:
            print(f"[INFO] Codex config exists but no prompt: {codex_cfg}")

    # integrity
    for name in ["gpt-5.6-sol-v45.md", "gpt-6-astra-v1.md"]:
        p = SKILL / "prompts" / name
        if p.exists():
            print(f"  {name}: {file_sha256(p)[:16]} {p.stat().st_size}B")

    print("\n=== RESULT ===")
    print("PASS" if ok else "FAIL (skill eksik)")
    print("\nTest: opencode içinde 'gpt-instruct deploy et' yaz veya:")
    print(f'  python \"{SKILL}/src/opencode_instruct.py\" --status')
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(check())
