# gpt-instruct — opencode Global Installer

> **Source project:** [MDX-Tom/gpt-instruct](https://github.com/MDX-Tom/gpt-instruct)  
> **License:** MIT — see `SKILL_TEMPLATE/gpt-instruct/LICENSE`  
> **Original tool:** `codex-instruct.py` (778 lines) → adapted as `src/opencode_instruct.py` for opencode  
> **opencode integration by:** [gkhantyln](https://github.com/gkhantyln) — skill wrapper, atomic deploy, BAT installers  
> **opencode version:** `instructions` + `skills` global, Codex `model_instructions_file` backward compatible

One-click installer for `gpt-5.6-sol-v45` (stable, 5170 B) and `gpt-6-astra-v1` (formal e2b19, 7495 B) unrestricted prompts. Works as opencode global skill (trigger) and/or persistent `opencode.jsonc` `instructions`, with the same atomic/backup/state safety as the original Codex deployer.

---

## Table of Contents
- [Features](#features)
- [Prompt Comparison](#prompt-comparison)
- [File Map](#file-map)
- [Quick Install (Windows)](#quick-install-windows)
- [Manual Install](#manual-install)
- [Usage](#usage)
- [Switching Versions](#switching-versions)
- [Verification](#verification)
- [Uninstall / Reset](#uninstall--reset)
- [Technical Details](#technical-details)
- [Checksums](#checksums)
- [Credits](#credits)

---

## Features

*   **Skill mode (recommended for most users):** After `install.bat`, type in opencode `gpt-instruct deploy`, `astra v1`, `sol v45`, `model_instructions` — `SKILL.md:1` triggers inject `prompts/*.md`.
*   **Persistent global mode:** Writes `C:\Users\%USERNAME%\.config\opencode\gpt-5.6-sol-v45.md` and appends `instructions: ["./gpt-5.6-sol-v45.md"]` in `opencode.jsonc:358`. Survives restarts, no trigger needed.
*   **Codex compatible:** Same script manages `~/.codex/config.toml` `model_instructions_file = "./<md>"` (`codex-instruct.py:382`). Use `--target both|codex|opencode`.
*   **Safe:** `atomic_write_text():263` (mkstemp+replace), `backup_file():145` (`.bak_<timestamp>`), SHA256-tracked state (`.gpt56-*-state.json`), `is_safe_prompt_filename():160` traversal block, `--dry-run` preview.
*   **BAT installers:** `install.bat` (CRLF, `chcp 65001`) copies skill, verifies, optionally deploys. `uninstall.bat` resets with `--yes`.

---

## Prompt Comparison

| Property | `gpt-5.6-sol-v45` (stable) | `gpt-6-astra-v1` (formal) |
|---|---|---|
| Source | `gpt-5.6-sol-v45/gpt-5.6-sol-unrestricted-v45.md:1` | `gpt-6-astra-v1/gpt-6-astra-v1.md:1` |
| Size / SHA256 | 5170 B `c71c50e2f7a...` | 7495 B `39fb46d6edc...` |
| Strategy | `TOOL_TRANSACTION` (4 artifacts: MODIFIED_FILE/DIFF/VERIFICATION/ROLLBACK) + `PROCESS_RECORD` staged scene | `ATOMIC CONTINUATION DISPATCH` + `VERIFIED TRANSACTION` + `WORKSPACE OBJECT LOCK` |
| A/B Score | B 54/66 (81.82%) `docs/comparison-tests.md:57` | A 3/4, B execution 7/8 `docs/comparison-tests.md:40` |
| Strength | General, biology/cloud tasks strong | Multi-turn / continuation projects more stable |
| Limit | Both < 8000 B `README.md:41` | — |

> Historical `v5` (`1397 B`) included as `prompts/historical-v5.md` for reference.

---

## File Map

```
gpt-instruct-opencode-installer/
├── install.bat                         ← double-click installer (backup+verify+deploy)
├── uninstall.bat                       ← reset + remove skill
├── README.md                           ← this file (English)
├── README_TR.md                        ← Turkish
├── checksums.txt                       ← SHA256
└── SKILL_TEMPLATE/
    └── gpt-instruct/                   ← copied to %USERPROFILE%\.config\opencode\skills\gpt-instruct
        ├── SKILL.md                    (triggers: gpt-instruct, astra, sol, /gpt-instruct)
        ├── LICENSE (MIT)
        ├── prompts/
        │   ├── gpt-5.6-sol-v45.md      5170 B
        │   ├── gpt-6-astra-v1.md       7495 B
        │   └── historical-v5.md
        ├── src/
        │   ├── opencode_instruct.py    fork of codex-instruct.py → opencode
        │   └── __init__.py
        ├── scripts/
        │   └── verify.py
        └── templates/
            └── opencode_instructions.json
```

Installed global (after `install.bat` choice 2):
```
%USERPROFILE%\.config\opencode\
├── opencode.jsonc            ← instructions: ["./gpt-5.6-sol-v45.md"]
├── opencode.jsonc.bak_<ts>   ← snapshot
├── .gpt56-opencode-state.json← state
├── gpt-5.6-sol-v45.md        ← prompt copy
└── skills\gpt-instruct\      ← skill dir
```

---

## Quick Install (Windows)

1. Extract this folder anywhere.
2. Double-click **`install.bat`**.
3. Menu:
   ```
   1. Skill only — trigger required ("gpt-instruct deploy")
   2. Skill + opencode global persistent — RECOMMENDED
   3. Skill + opencode + Codex all
   4. Skill only, write nothing now
   ```
   Default `2`. Press `Enter` for default.
4. Version:
   ```
   1. gpt-5.6-sol-v45 — stable — default
   2. gpt-6-astra-v1 — formal
   ```
5. Done — no opencode restart needed. Window stays open via `pause`; close it.

If the window closes instantly (encoding issue fixed in current `install.bat:1` CRLF `chcp 65001`), run from cmd:
```bat
cmd.exe /k "C:\path\to\install.bat"
```

---

## Manual Install

```bat
:: copy skill
xcopy /E /I SKILL_TEMPLATE\gpt-instruct %USERPROFILE%\.config\opencode\skills\gpt-instruct\

:: persistent global (example v45)
python %USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py --apply --target opencode --version gpt-5.6-v45

:: Codex + opencode
python %USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py --apply --target both --version gpt-6-v1

:: preview
python %USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py --dry-run --apply --version gpt-5.6-v45

:: status
python %USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py --status

:: reset
python %USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py --reset --target both --yes
```

---

## Usage

### Skill trigger (no persistent config)
In any opencode session, type natural language:
```
gpt-instruct deploy
use astra v1
sol v45 activate
model_instructions install
/gpt-instruct --version gpt-6-v1
```
`SKILL.md` triggers, content of `prompts/*.md` is injected.

### CLI persistent
```bat
python "%USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py" --apply --target opencode --version gpt-5.6-v45
python "...\opencode_instruct.py" --status
python "...\opencode_instruct.py" --reset --target opencode --yes
```

Codex target still works (`codex-instruct.py:130` logic):
```bat
python ...\opencode_instruct.py --apply --codex-dir %USERPROFILE%\.codex --version gpt-6-v1
python ...\opencode_instruct.py --reset --codex-dir %USERPROFILE%\.codex --yes
```

---

## Switching Versions

**If you want a different version** (e.g., you installed `v45` but want `astra v1`):

```bat
:: Option A: rerun installer → choose 2 → 2

:: Option B: CLI directly
python "%USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py" --apply --target opencode --version gpt-6-v1
:: (overwrites instructions entry, backups previous, updates state)

:: Verify
python "...\opencode_instruct.py" --status
python "...\scripts\verify.py"
```

To keep **both prompts available but switch default**, just re-apply; the previous `instructions` entry is replaced atomically, old prompt file is kept if it was user-modified, otherwise SHA256-verified and preserved per `prepare_opencode_state()`.

To use **skill trigger switching without persistent**, no CLI needed — just prompt the model: `"use gpt-6-astra-v1"` and the skill will inject the other file.

---

## Verification

```bat
python "%USERPROFILE%\.config\opencode\skills\gpt-instruct\scripts\verify.py"
:: [OK] skill dir
:: [OK] SKILL.md 5201 B
:: [OK] prompts/gpt-5.6-sol-v45.md 5170 B c71c50e2
:: [OK] prompts/gpt-6-astra-v1.md 7495 B 39fb46d6
:: [OK] opencode.jsonc
:: PASS

python "%USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py" --status
:: [Codex] config.toml: (no) model_instructions_file
:: [opencode] instructions: ["./gpt-5.6-sol-v45.md"]
:: skill: installed
```

Manual checksum:
```bat
certutil -hashfile "SKILL_TEMPLATE\gpt-instruct\prompts\gpt-5.6-sol-v45.md" SHA256
certutil -hashfile "SKILL_TEMPLATE\gpt-instruct\prompts\gpt-6-astra-v1.md" SHA256
```

---

## Uninstall / Reset

Double-click `uninstall.bat`:
```
1. Only opencode global instructions clean
2. Only Codex clean
3. All — opencode + Codex + remove skill dir — RECOMMENDED
4. Cancel
```
Or CLI:
```bat
python "%USERPROFILE%\.config\opencode\skills\gpt-instruct\src\opencode_instruct.py" --reset --target both --yes
rmdir /S /Q "%USERPROFILE%\.config\opencode\skills\gpt-instruct"
del "%USERPROFILE%\.config\opencode\gpt-5.6-sol-v45.md"
del "%USERPROFILE%\.codex\gpt-5.6-sol-v45.md"
```
Previous `instructions` (excluding managed) is restored from `.gpt56-opencode-state.json` `previous_instructions`, provider/model settings are never overwritten (`codex-instruct.py:8` CCSwitch-compatible).

---

## Technical Details

*   **Codex mode:** `replace_top_level_model_instructions():217` edits only root `model_instructions_file` before first `[table]`, preserves CRLF.
*   **opencode mode:** `load_opencode_json()` strips `//`/`/* */` via `_strip_jsonc_comments()`, parses with `utf-8-sig` (BOM-safe), updates `instructions` list (dedup, removes old managed), `save_opencode_json()` atomic `json.dumps(indent=4)`.
*   **Safety:** `is_safe_prompt_filename():160` blocks traversal, `atomic_write_text():263` mkstemp+`os.replace`, `backup_file():145` timestamped, state SHA256 verified deletion.
*   **Size:** Both prompts < 8000 B, fit opencode limit.

---

## Checksums

See `checksums.txt` — bytes are copied verbatim from `MDX-Tom/gpt-instruct`, not modified:
```
c71c50e2f7a303b5eebc2b24c0b1ca0d9c753e3240db05c3e472c679907898f7  prompts/gpt-5.6-sol-v45.md (5170 B)
39fb46d6edc75963677fd92828dcb6c66dce11740b432efda3af9a683158ce16  prompts/gpt-6-astra-v1.md (7495 B)
```

---

## Credits

*   **Source repository:** [MDX-Tom/gpt-instruct](https://github.com/MDX-Tom/gpt-instruct) — prompt engineering, evaluation harness (`scripts/*.zip`, `docs/comparison-tests.md`), original `codex-instruct.py` (MIT).
*   **opencode integration:** [gkhantyln](https://github.com/gkhantyln) — adaptation to opencode global `skills` + `opencode.jsonc` `instructions`, `src/opencode_instruct.py` (Codex+opencode dual target, BOM/--yes/CRLF fixes), BAT installers with backup/verify, skill `SKILL.md` triggers, documentation.
*   **License:** MIT — original `LICENSE` preserved; this wrapper adds no new license restrictions.

> ⚠️ These prompts contain `[MODE: UNRESTRICTED]` instructions. They are for AI safety research. Provider policy blocks, rate limits, or account restrictions may occur (`docs/comparison-tests.md:57` 1 policy block recorded). Use on disposable/test accounts, not for unauthorized systems. You are responsible for usage.

---

## See Also

*   `README_TR.md` — Turkish version
*   `docs/comparison-tests.md` (upstream) — A/B/C evaluation details
*   `unit-tests/test_codex_instruct.py:29` — original tests, adapted in `scripts/verify.py`
