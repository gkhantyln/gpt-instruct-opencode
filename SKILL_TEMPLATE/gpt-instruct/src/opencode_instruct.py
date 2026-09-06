#!/usr/bin/env python3
"""Deploy or remove gpt-instruct prompts for Codex and opencode.

Fork of codex-instruct.py (778 lines) — original logic preserved, extended for opencode global.

Codex:  writes `model_instructions_file = "./<md>"` to CODEX_HOME/config.toml
opencode: writes prompt file to OPENCODE_HOME/<md> and manages `instructions: ["./<md>"]` in opencode.jsonc/json

State/backup/atomic handling mirrors codex-instruct.py:145,263,156 to stay safe for CCSwitch / provider configs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path

# Windows cp1254 fix — force utf-8 or replace errors to avoid UnicodeEncodeError on banner
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------------------------------------------------------------------------
# Paths — skill root detection (works both inside installed skill and installer)
# ---------------------------------------------------------------------------
def _skill_root() -> Path:
    # src/opencode_instruct.py -> skill root = parent.parent
    p = Path(__file__).resolve().parent.parent
    # if prompts not found, try PROJECT_ROOT fallback (installer run)
    if (p / "prompts").exists():
        return p
    # fallback: try git root style
    return p

SKILL_ROOT = _skill_root()
PROJECT_ROOT = SKILL_ROOT  # alias for compat

DEFAULT_PROMPT_VERSION = "gpt-5.6-v45"
PROMPT_VERSIONS: dict[str, tuple[Path, str]] = {
    "gpt-5.6-v45": (
        SKILL_ROOT / "prompts" / "gpt-5.6-sol-v45.md",
        "gpt-5.6-sol-v45.md",
    ),
    "gpt-6-v1": (
        SKILL_ROOT / "prompts" / "gpt-6-astra-v1.md",
        "gpt-6-astra-v1.md",
    ),
}
DEFAULT_PROMPT_MD_FILENAME = PROMPT_VERSIONS[DEFAULT_PROMPT_VERSION][1]

# Also accept legacy filenames so reset can clean old installs
LEGACY_MANAGED_PROMPT_FILENAMES = {
    "gpt-5.6-sol-unrestricted-v45.md",
    "gpt-5.6-sol-unrestricted-v5.md",
    "gpt-5.6-sol-unrestricted-v35.md",
    "gpt-5.6-sol-unrestricted-v41.md",
    "gpt-5.6-sol-unrestricted-v41-skills.md",
    "gpt-5.6-sol-unrestricted-v42.md",
    "gpt-6-astra-v1-rc1.md",
    "historical-v5.md",
}
MANAGED_PROMPT_FILENAMES = {
    *(md_filename for _, md_filename in PROMPT_VERSIONS.values()),
    *LEGACY_MANAGED_PROMPT_FILENAMES,
}

BASELINE_BACKUP_SUFFIX = ".gpt56-sol-instruct.bak"
STATE_FILENAME = ".gpt56-sol-instruct-state.json"
OPENCODE_STATE_FILENAME = ".gpt56-opencode-state.json"
STATE_VERSION = 2
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MODEL_INSTRUCTIONS_PATTERN = re.compile(
    r"^\s*model_instructions_file\s*=\s*(['\"])(.*?)\1\s*(?:#.*)?$"
)

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DARK_GREEN = "\033[38;2;0;100;0m"
BANNER_WIDTH = 72

def color_enabled() -> bool:
    if os.environ.get("FORCE_COLOR") is not None:
        return True
    return sys.stdout.isatty()

def styled(text: str, *codes: str) -> str:
    if not color_enabled():
        return text
    return f"{''.join(codes)}{text}{ANSI_RESET}"

def display_width(text: str) -> int:
    return sum(2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1 for char in text)

def section_banner(title: str) -> str:
    label = f" {title} "
    fill_width = max(4, BANNER_WIDTH - display_width(label))
    left = fill_width // 2
    right = fill_width - left
    try:
        bar = "━"
        # test if stdout can encode it
        bar.encode(sys.stdout.encoding or "utf-8", errors="strict")
    except Exception:
        bar = "="
    return styled(f"{bar * left}{label}{bar * right}", ANSI_BOLD)

def intro_text() -> str:
    zh_banner = section_banner("中文说明")
    en_banner = section_banner("English Instructions")
    zh_title = styled("gpt-instruct 版本部署说明：", ANSI_BOLD)
    en_title = styled("gpt-instruct version deployment:", ANSI_BOLD)
    zh_default = styled("唯一默认版", ANSI_BOLD, ANSI_DARK_GREEN)
    en_default = styled("sole default release", ANSI_BOLD, ANSI_DARK_GREEN)
    return f"""\
{zh_banner}
{zh_title}

gpt-5.6-sol-v45 是当前生产使用的{zh_default}；gpt-6-astra-v1 是可选的 gpt-6-astra 首个正式版。
opencode 适配版：同时支持 Codex CODEX_HOME/config.toml 和 opencode OPENCODE_HOME/opencode.jsonc

{en_banner}
{en_title}

gpt-5.6-sol-v45 is the current {en_default}; gpt-6-astra-v1 is optional.
opencode adapter: supports both Codex and opencode global. Use --target to select.
"""

def menu_text() -> str:
    selection_banner = section_banner("操作选择 / Select an Action")
    default = styled("默认 / Default", ANSI_BOLD, ANSI_DARK_GREEN)
    return f"""\
{selection_banner}
1. gpt-5.6-v45 → gpt-5.6-sol-v45 （{default}） [codex+opencode]
2. gpt-6-v1 → gpt-6-astra-v1 （formal release） [codex+opencode]
3. 去除提示词并恢复原配置项 / Remove managed instructions
4. 仅 opencode global / opencode only
5. 仅 Codex / codex only
q. 退出而不执行任何操作 / Quit without modification
"""

# ---------------------------------------------------------------------------
# Codex helpers — preserved verbatim from codex-instruct.py:130
# ---------------------------------------------------------------------------

def find_codex_dirs() -> list[Path]:
    candidates: set[Path] = set()
    env_home = os.environ.get("CODEX_HOME")
    if env_home:
        candidates.add(Path(env_home).expanduser())
    candidates.add(Path.home() / ".codex")
    return sorted(path.resolve() for path in candidates if (path / "config.toml").exists())

def selected_codex_dirs(codex_dir: str | None) -> list[Path]:
    if codex_dir:
        return [Path(codex_dir).expanduser().resolve()]
    return find_codex_dirs()

def backup_file(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup = path.with_suffix(path.suffix + f".bak_{timestamp}")
    shutil.copy2(path, backup)
    return backup

def baseline_backup_path(config_path: Path) -> Path:
    return config_path.with_name(config_path.name + BASELINE_BACKUP_SUFFIX)

def state_file_path(config_path: Path) -> Path:
    return config_path.parent / STATE_FILENAME

def opencode_state_file_path(config_path: Path) -> Path:
    return config_path.parent / OPENCODE_STATE_FILENAME

def is_safe_prompt_filename(filename: object) -> bool:
    return (
        isinstance(filename, str)
        and bool(filename)
        and "/" not in filename
        and "\\" not in filename
        and filename.lower().endswith(".md")
        and Path(filename).name == filename
    )

def prompt_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def is_valid_instruction_line(line: object) -> bool:
    return (
        isinstance(line, str)
        and "\n" not in line
        and "\r" not in line
        and MODEL_INSTRUCTIONS_PATTERN.fullmatch(line) is not None
    )

def top_level_model_instructions_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("["):
            break
        if re.match(r"^\s*model_instructions_file\s*=", line):
            return line
    return None

def line_references_managed_prompt(line: str | None, filenames: set[str]) -> bool:
    if not line:
        return False
    match = MODEL_INSTRUCTIONS_PATTERN.fullmatch(line)
    if not match:
        return False
    reference = match.group(2).replace("\\", "/")
    if reference.startswith("./"):
        reference = reference[2:]
    if "/" in reference:
        return False
    return reference in filenames

def replace_top_level_model_instructions(text: str, replacement: str | None) -> str:
    lines = text.splitlines(keepends=True)
    table_index = next(
        (index for index, line in enumerate(lines) if line.lstrip().startswith("[")),
        len(lines),
    )
    assignment_indexes = [
        index
        for index, line in enumerate(lines[:table_index])
        if re.match(r"^\s*model_instructions_file\s*=", line)
    ]
    if assignment_indexes:
        first = assignment_indexes[0]
        newline = (
            "\r\n"
            if lines[first].endswith("\r\n")
            else "\n"
            if lines[first].endswith("\n")
            else ""
        )
        if replacement is None:
            del lines[first]
        else:
            lines[first] = replacement + newline
        return "".join(lines)
    if replacement is None:
        return text
    insert_at = next(
        (
            index + 1
            for index, line in enumerate(lines[:table_index])
            if re.match(r"^\s*model\s*=", line)
        ),
        table_index,
    )
    newline = "\r\n" if any(line.endswith("\r\n") for line in lines) else "\n"
    if insert_at > 0 and lines[insert_at - 1] and not lines[insert_at - 1].endswith("\n"):
        lines[insert_at - 1] += newline
    lines.insert(insert_at, replacement + newline)
    return "".join(lines)

def atomic_write_text(path: Path, text: str, *, follow_symlink: bool = False) -> None:
    if path.is_symlink() and not follow_symlink:
        raise OSError(f"refusing to overwrite symlink: {path}")
    write_path = path.resolve(strict=False) if path.is_symlink() else path
    previous_mode = write_path.stat().st_mode & 0o777 if write_path.exists() else 0o600
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{write_path.name}.",
        dir=write_path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, previous_mode)
        os.replace(temporary_path, write_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

def read_state(config_path: Path) -> dict[str, object] | None:
    path = state_file_path(config_path)
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(state, dict) or state.get("version") != STATE_VERSION:
        return None
    previous_line = state.get("previous_model_instructions_line")
    if previous_line is not None and not is_valid_instruction_line(previous_line):
        return None
    stored_prompts = state.get("managed_prompts")
    if not isinstance(stored_prompts, dict):
        return None
    managed_prompts: dict[str, dict[str, object]] = {}
    for filename, metadata in stored_prompts.items():
        if not is_safe_prompt_filename(filename) or not isinstance(metadata, dict):
            return None
        digest = metadata.get("sha256")
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            return None
        existed_before = metadata.get("existed_before")
        if not isinstance(existed_before, bool):
            return None
        managed_prompts[filename] = {"sha256": digest, "existed_before": existed_before}
    return {"version": STATE_VERSION, "previous_model_instructions_line": previous_line, "managed_prompts": managed_prompts}

def save_state(config_path: Path, state: dict[str, object]) -> None:
    atomic_write_text(state_file_path(config_path), json.dumps(state, ensure_ascii=False, indent=2) + "\n")

def read_opencode_state(config_path: Path) -> dict[str, object] | None:
    path = opencode_state_file_path(config_path)
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(state, dict) or state.get("version") != STATE_VERSION:
        return None
    return state

def save_opencode_state(config_path: Path, state: dict[str, object]) -> None:
    atomic_write_text(opencode_state_file_path(config_path), json.dumps(state, ensure_ascii=False, indent=2) + "\n")

def previous_instruction_from_legacy_baseline(config_path: Path) -> str | None:
    baseline = baseline_backup_path(config_path)
    if not baseline.exists():
        return None
    line = top_level_model_instructions_line(baseline.read_text(encoding="utf-8"))
    if line_references_managed_prompt(line, MANAGED_PROMPT_FILENAMES):
        return None
    return line

def prepare_deployment_state(config_path: Path, md_filename: str, prompt_text: str, existed_before: bool = False) -> dict[str, object]:
    state = read_state(config_path)
    if state is None:
        current_line = top_level_model_instructions_line(config_path.read_text(encoding="utf-8") if config_path.exists() else "")
        if line_references_managed_prompt(current_line, MANAGED_PROMPT_FILENAMES | {md_filename}):
            current_line = previous_instruction_from_legacy_baseline(config_path)
        state = {"version": STATE_VERSION, "previous_model_instructions_line": current_line, "managed_prompts": {}}
    managed_prompts = state["managed_prompts"]
    assert isinstance(managed_prompts, dict)
    previous_metadata = managed_prompts.get(md_filename)
    was_preexisting = previous_metadata.get("existed_before", existed_before) if isinstance(previous_metadata, dict) else existed_before
    managed_prompts[md_filename] = {"sha256": prompt_sha256(prompt_text), "existed_before": bool(was_preexisting)}
    save_state(config_path, state)
    return state

def set_model_instructions(config_path: Path, md_filename: str) -> bool:
    text = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    target = f'model_instructions_file = "./{md_filename}"'
    new_text = replace_top_level_model_instructions(text, target)
    if new_text != text:
        atomic_write_text(config_path, new_text, follow_symlink=True)
        return True
    return False

def restore_managed_model_instructions(config_path: Path) -> tuple[bool, str]:
    if not config_path.exists():
        return False, "missing"
    state = read_state(config_path)
    managed_filenames = set(MANAGED_PROMPT_FILENAMES)
    if state:
        stored_prompts = state.get("managed_prompts", {})
        if isinstance(stored_prompts, dict):
            managed_filenames.update(stored_prompts)
    text = config_path.read_text(encoding="utf-8")
    current_line = top_level_model_instructions_line(text)
    if not line_references_managed_prompt(current_line, managed_filenames):
        return False, "not-managed"
    previous_line = state.get("previous_model_instructions_line") if state else None
    if previous_line is not None and not isinstance(previous_line, str):
        previous_line = None
    if state is None:
        previous_line = previous_instruction_from_legacy_baseline(config_path)
    new_text = replace_top_level_model_instructions(text, previous_line)
    if new_text != text:
        atomic_write_text(config_path, new_text, follow_symlink=True)
        return True, "restored" if previous_line else "removed"
    return False, "unchanged"

# ---------------------------------------------------------------------------
# opencode helpers
# ---------------------------------------------------------------------------

def find_opencode_config() -> Path | None:
    """Locate opencode global config: prefers opencode.jsonc, fallback json."""
    candidates = []
    env_home = os.environ.get("OPENCODE_HOME")
    if env_home:
        candidates.append(Path(env_home).expanduser())
    # standard global location
    candidates.append(Path.home() / ".config" / "opencode")
    # also check USERPROFILE/.config/opencode on Windows
    # Path.home() already covers it
    for base in candidates:
        for name in ("opencode.jsonc", "opencode.json"):
            p = base / name
            if p.exists():
                return p
    # if none exists, return default path to create
    return Path.home() / ".config" / "opencode" / "opencode.jsonc"

def find_opencode_dirs() -> list[Path]:
    cfg = find_opencode_config()
    if cfg and cfg.exists():
        return [cfg.parent]
    return []

def selected_opencode_dirs(opencode_dir: str | None) -> list[Path]:
    if opencode_dir:
        return [Path(opencode_dir).expanduser().resolve()]
    # if no config exists yet, still return default dir so we can create
    cfg = find_opencode_config()
    if cfg:
        # ensure parent exists check not needed; we will create
        parent = cfg.parent if cfg.exists() else Path.home() / ".config" / "opencode"
        if parent.exists():
            return [parent.resolve()]
        # if not exists, try to find code path? just return default
        return [parent.resolve()]
    return find_opencode_dirs()

def _strip_jsonc_comments(text: str) -> str:
    # remove // comments and /* */ blocks, preserving strings
    # simple state machine
    out = []
    i = 0
    in_str = False
    str_char = ""
    esc = False
    in_single_comment = False
    in_multi_comment = False
    while i < len(text):
        c = text[i]
        nxt = text[i+1] if i+1 < len(text) else ""
        if in_single_comment:
            if c == "\n":
                in_single_comment = False
                out.append(c)
            i += 1
            continue
        if in_multi_comment:
            if c == "*" and nxt == "/":
                in_multi_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == str_char:
                in_str = False
            i += 1
            continue
        # not in string/comment
        if c in ('"', "'"):
            in_str = True
            str_char = c
            out.append(c)
        elif c == "/" and nxt == "/":
            in_single_comment = True
            i += 1
        elif c == "/" and nxt == "*":
            in_multi_comment = True
            i += 1
        else:
            out.append(c)
        i += 1
    return "".join(out)

def load_opencode_json(config_path: Path) -> tuple[dict, str]:
    raw = config_path.read_text(encoding="utf-8-sig") if config_path.exists() else '{\n  "instructions": []\n}\n'
    stripped = _strip_jsonc_comments(raw)
    try:
        data = json.loads(stripped) if stripped.strip() else {}
    except json.JSONDecodeError as e:
        print(f"[警告] opencode config JSON parse failed, using empty: {e}", file=sys.stderr)
        data = {}
    return data, raw

def save_opencode_json(config_path: Path, data: dict, original_raw: str | None = None) -> None:
    # Preserve formatting minimally: dump with 2 spaces, keep order
    # If original had comments, we will overwrite without comments (acceptable for global config)
    text = json.dumps(data, ensure_ascii=False, indent=4)
    # ensure trailing newline
    if not text.endswith("\n"):
        text += "\n"
    atomic_write_text(config_path, text, follow_symlink=True)

def get_instructions_list(data: dict) -> list[str]:
    instr = data.get("instructions")
    if instr is None:
        return []
    if isinstance(instr, list):
        return [str(x) for x in instr]
    if isinstance(instr, str):
        return [instr]
    return []

def set_opencode_instructions(config_path: Path, md_filename: str) -> bool:
    data, raw = load_opencode_json(config_path)
    instr = get_instructions_list(data)
    target_variants = {f"./{md_filename}", md_filename, f".config/opencode/{md_filename}"}
    # normalize existing
    normalized = [s.replace("\\", "/") for s in instr]
    # check if already contains managed entry
    has_managed = any(s in MANAGED_PROMPT_FILENAMES or s.replace("./","") in MANAGED_PROMPT_FILENAMES for s in normalized)
    # check if target already present
    if f"./{md_filename}" in instr or md_filename in instr:
        return False
    # remove old managed entries
    cleaned = [s for s in instr if s.replace("./","").replace("\\","/") not in MANAGED_PROMPT_FILENAMES]
    cleaned.append(f"./{md_filename}")
    if cleaned == instr:
        return False
    data["instructions"] = cleaned
    # ensure skills.paths includes skill dir
    # no need to modify
    save_opencode_json(config_path, data, raw)
    return True

def restore_opencode_instructions(config_path: Path) -> tuple[bool, str]:
    if not config_path.exists():
        return False, "missing"
    data, raw = load_opencode_json(config_path)
    instr = get_instructions_list(data)
    if not instr:
        return False, "not-managed"
    managed = set(MANAGED_PROMPT_FILENAMES)
    # find if any instruction references managed prompt
    has_managed = any(s.replace("./","").replace("\\","/") in managed for s in instr)
    if not has_managed:
        return False, "not-managed"
    # check state for previous instructions
    state = read_opencode_state(config_path)
    previous = None
    if state and "previous_instructions" in state:
        prev = state.get("previous_instructions")
        if isinstance(prev, list):
            previous = prev
    # else fallback to removing managed entries
    new_instr = [s for s in instr if s.replace("./","").replace("\\","/") not in managed]
    if previous is not None:
        # if previous was empty list, use that
        new_instr = previous
    if new_instr == instr:
        return False, "unchanged"
    data["instructions"] = new_instr
    save_opencode_json(config_path, data, raw)
    return True, "restored" if previous else "removed"

def prepare_opencode_state(config_path: Path, md_filename: str, prompt_text: str, existed_before: bool = False) -> dict[str, object]:
    state = read_opencode_state(config_path)
    data, _ = load_opencode_json(config_path)
    current_instr = get_instructions_list(data)
    if state is None:
        # save current non-managed instructions as previous
        state = {"version": STATE_VERSION, "previous_instructions": current_instr, "managed_prompts": {}}
        # filter out managed if present? keep as is for restore
        # if current already has managed, previous should be without it
        filtered = [s for s in current_instr if s.replace("./","") not in MANAGED_PROMPT_FILENAMES and s not in MANAGED_PROMPT_FILENAMES]
        state["previous_instructions"] = filtered
    managed = state.get("managed_prompts", {})
    assert isinstance(managed, dict)
    prev_meta = managed.get(md_filename)
    was = prev_meta.get("existed_before", existed_before) if isinstance(prev_meta, dict) else existed_before
    managed[md_filename] = {"sha256": prompt_sha256(prompt_text), "existed_before": bool(was)}
    state["managed_prompts"] = managed
    save_opencode_state(config_path, state)
    return state

def read_prompt(source_path: Path, expected_md_filename: str) -> str:
    if source_path.suffix.lower() != ".zip":
        return source_path.read_text(encoding="utf-8")
    with zipfile.ZipFile(source_path) as archive:
        files = [name for name in archive.namelist() if not name.endswith("/")]
        preferred = [name for name in files if Path(name).name == expected_md_filename]
        markdown_files = [name for name in files if Path(name).suffix.lower() == ".md"]
        candidates = preferred or markdown_files
        if len(candidates) != 1:
            raise ValueError(f"压缩包应包含唯一的 {expected_md_filename}（或唯一 Markdown 文件），实际候选: {candidates}")
        member = candidates[0]
        with tempfile.TemporaryDirectory(prefix="gpt56-sol-prompt-") as temp_dir:
            extracted_path = Path(archive.extract(member, path=temp_dir))
            return extracted_path.read_text(encoding="utf-8")

def deploy_prompt(args: argparse.Namespace, prompt_path: Path, md_filename: str) -> int:
    if not is_safe_prompt_filename(md_filename):
        print(f"[错误] 目标名称必须是不含路径的 .md 文件名: {md_filename}", file=sys.stderr)
        return 2
    if not prompt_path.exists():
        print(f"[错误] 提示词文件不存在: {prompt_path}", file=sys.stderr)
        return 2

    # Determine targets
    target = getattr(args, "target", "both")
    do_codex = target in ("both", "codex")
    do_opencode = target in ("both", "opencode")

    codex_dirs = selected_codex_dirs(args.codex_dir) if do_codex else []
    # if do_codex but no dirs found and user explicitly asked codex, error
    if do_codex and not codex_dirs and getattr(args, "codex_dir", None):
        print(f"[错误] Codex dir bulunamadı: {args.codex_dir}", file=sys.stderr)
        return 2
    # if auto and none found, silently skip codex
    if do_codex and not codex_dirs:
        print("[*] Codex config bulunamadı, sadece opencode hedeflenecek ( --target codex ile zorlayın )")

    opencode_dirs = selected_opencode_dirs(getattr(args, "opencode_dir", None)) if do_opencode else []
    if do_opencode and not opencode_dirs:
        print("[错误] opencode config dizini bulunamadı; --opencode-dir ile belirtin", file=sys.stderr)
        return 2

    try:
        prompt_text = read_prompt(prompt_path, md_filename)
    except (OSError, UnicodeError, ValueError, zipfile.BadZipFile) as exc:
        print(f"[错误] 读取或解压提示词失败: {exc}", file=sys.stderr)
        return 2

    source_kind = "ZIP（已解压校验）" if prompt_path.suffix.lower() == ".zip" else "Markdown"
    print(f"[+] Prompt: {prompt_path} [{source_kind}]")
    print(f"    SHA256: {prompt_sha256(prompt_text)[:16]}... ({len(prompt_text.encode('utf-8'))} bytes)")

    exit_code = 0

    # --- Codex deploy ---
    for codex_dir in codex_dirs:
        config_path = codex_dir / "config.toml"
        destination = codex_dir / md_filename
        print(f"\n── Codex 目标 / Target: {codex_dir} ──")
        print(f"  写入 / Write: {destination}")
        print(f'  配置 / Config: model_instructions_file = "./{md_filename}"')
        if args.dry_run:
            continue
        codex_dir.mkdir(parents=True, exist_ok=True)
        if not config_path.exists():
            atomic_write_text(config_path, "", follow_symlink=True)
            print("  创建 / Created: config.toml")
        if state_file_path(config_path).is_symlink():
            print(f"[错误] 状态文件不能是符号链接: {state_file_path(config_path)}", file=sys.stderr)
            return 2
        state = read_state(config_path)
        tracked_prompts = state.get("managed_prompts", {}) if state else {}
        current_line = top_level_model_instructions_line(config_path.read_text(encoding="utf-8"))
        legacy_owned = state is None and line_references_managed_prompt(current_line, {md_filename})
        if ((destination.exists() or destination.is_symlink()) and md_filename not in tracked_prompts and not legacy_owned):
            print(f"[错误] 目标文件已存在且不属于本脚本，未覆盖: {destination}", file=sys.stderr)
            print("[Error] Destination exists but is not owned; choose another --name.", file=sys.stderr)
            return 2
        snapshot = backup_file(config_path)
        print(f"  已创建操作前备份 / Snapshot saved: {snapshot.name}")
        prepare_deployment_state(config_path, md_filename, prompt_text, existed_before=destination.exists() or destination.is_symlink())
        atomic_write_text(destination, prompt_text)
        changed = set_model_instructions(config_path, md_filename)
        print("  状态 / Status:", "已更新 / Updated" if changed else "已是最新 / Already current")

    # --- opencode deploy ---
    for opencode_dir in opencode_dirs:
        # find config file (jsonc preferred)
        cfg_path = None
        for name in ("opencode.jsonc", "opencode.json"):
            p = opencode_dir / name
            if p.exists():
                cfg_path = p
                break
        if cfg_path is None:
            cfg_path = opencode_dir / "opencode.jsonc"
            # create minimal if not exists
            if not cfg_path.exists():
                opencode_dir.mkdir(parents=True, exist_ok=True)
                cfg_path.write_text('{\n  "instructions": []\n}\n', encoding="utf-8")
                print(f"  创建 / Created: {cfg_path}")
        destination = opencode_dir / md_filename
        print(f"\n── opencode 目标 / Target: {opencode_dir} ──")
        print(f"  写入 / Write: {destination}")
        print(f'  配置 / Config: instructions = ["./{md_filename}"] in {cfg_path.name}')
        print("  兼容模式 / Compatibility: 仅修改本项目管理的 instructions 项")
        if args.dry_run:
            continue
        opencode_dir.mkdir(parents=True, exist_ok=True)
        if opencode_state_file_path(cfg_path).is_symlink():
            print(f"[错误] State symlink: {opencode_state_file_path(cfg_path)}", file=sys.stderr)
            return 2
        # check ownership
        state = read_opencode_state(cfg_path)
        tracked = state.get("managed_prompts", {}) if state else {}
        if (destination.exists() or destination.is_symlink()) and md_filename not in tracked:
            # allow if not tracked but is managed legacy? check hash?
            # if file exists and not owned, refuse
            # but if state is None and file is managed name, consider legacy_owned
            data, _ = load_opencode_json(cfg_path)
            instr = get_instructions_list(data)
            has_managed_instr = any(s.replace("./","") == md_filename for s in instr)
            if not has_managed_instr:
                print(f"[错误] 目标文件已存在且不属于本脚本，未覆盖: {destination}", file=sys.stderr)
                return 2
        if cfg_path.exists():
            snapshot = backup_file(cfg_path)
            print(f"  已创建操作前备份 / Snapshot saved: {snapshot.name}")
        prepare_opencode_state(cfg_path, md_filename, prompt_text, existed_before=destination.exists() or destination.is_symlink())
        atomic_write_text(destination, prompt_text)
        changed = set_opencode_instructions(cfg_path, md_filename)
        print("  状态 / Status:", "已更新 / Updated" if changed else "已是最新 / Already current")
        # also copy to skill prompts for trigger mode? already there via installer

    return exit_code

def confirm_reset(args: argparse.Namespace | None = None) -> bool:
    if args is not None and getattr(args, "yes", False):
        return True
    print("  将只恢复本脚本管理的 model_instructions_file / instructions，并移除提示词文件。")
    print("  provider、模型、认证及CCSwitch在部署后写入的其他配置均保持不变。")
    try:
        answer = input("确认继续？/ Confirm removal? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in {"y", "yes", "是"}

def reset_managed_install(args: argparse.Namespace) -> int:
    target = getattr(args, "target", "both")
    do_codex = target in ("both", "codex")
    do_opencode = target in ("both", "opencode")
    codex_dirs = selected_codex_dirs(args.codex_dir) if do_codex else []
    # if opencode explicitly requested but no dir, create list with default
    opencode_dirs = selected_opencode_dirs(getattr(args, "opencode_dir", None)) if do_opencode else []
    if do_opencode and not opencode_dirs:
        # fallback to default dir
        opencode_dirs = [Path.home() / ".config" / "opencode"]

    # Codex reset
    for codex_dir in codex_dirs:
        config_path = codex_dir / "config.toml"
        print(f"\n── Codex 目标 / Target: {codex_dir} ──")
        state = read_state(config_path)
        managed_prompts = state.get("managed_prompts", {}) if state else {}
        assert isinstance(managed_prompts, dict)
        if not confirm_reset(args):
            print("  未确认，已取消 / Confirmation not received; reset cancelled.")
            continue
        if args.dry_run:
            print("  预览完成，未修改文件 / Dry run complete; no files changed.")
            continue
        if config_path.exists():
            snapshot = backup_file(config_path)
            print(f"  已创建恢复前备份 / Pre-reset snapshot: {snapshot.name}")
        _changed, status = restore_managed_model_instructions(config_path)
        status_messages = {"restored": "已恢复原配置项 / Previous entry restored", "removed": "已移除脚本配置项 / Managed entry removed", "not-managed": "当前配置项不属于本脚本，保持不变 / Current entry left unchanged", "missing": "config.toml 不存在 / Not found", "unchanged": "无需修改 / No change needed"}
        print("  配置状态 / Config status:", status_messages[status])
        removed = preserved = 0
        for filename, metadata in managed_prompts.items():
            prompt_path = codex_dir / filename
            expected_digest = metadata.get("sha256") if isinstance(metadata, dict) else None
            existed_before = metadata.get("existed_before", True) if isinstance(metadata, dict) else True
            try:
                digest_matches = not existed_before and prompt_path.is_file() and bool(expected_digest) and file_sha256(prompt_path) == expected_digest
            except OSError:
                digest_matches = False
            if digest_matches:
                prompt_path.unlink()
                removed += 1
            elif prompt_path.exists():
                preserved += 1
                reason = "部署前已存在 / pre-existing" if existed_before else "用户已修改 / user-modified"
                print(f"  已保留文件 / Preserved file ({reason}): {prompt_path.name}")
        state_path = state_file_path(config_path)
        if state_path.exists():
            state_path.unlink()
        print(f"  提示词状态 / Prompt status: 已移除 {removed} 个，保留 {preserved} 个 / Removed {removed}, preserved {preserved}")

    # opencode reset
    for opencode_dir in opencode_dirs:
        cfg_path = None
        for name in ("opencode.jsonc", "opencode.json"):
            p = opencode_dir / name
            if p.exists():
                cfg_path = p
                break
        if cfg_path is None:
            print(f"\n── opencode 目标 / Target: {opencode_dir} ── (config not found, skip)")
            continue
        print(f"\n── opencode 目标 / Target: {opencode_dir} ──")
        print(f"  Config: {cfg_path}")
        state = read_opencode_state(cfg_path)
        managed_prompts = state.get("managed_prompts", {}) if state else {}
        if not state and not managed_prompts:
            # try to detect managed via instructions
            data, _ = load_opencode_json(cfg_path)
            instr = get_instructions_list(data)
            if not any(s.replace("./","") in MANAGED_PROMPT_FILENAMES for s in instr):
                print("  提示词 / Prompts: 无可信状态记录，不自动删除文件")
                # still try to restore instructions if managed
                pass
        if not confirm_reset(args):
            print("  未确认，已取消 / Confirmation not received; reset cancelled.")
            continue
        for filename in sorted(managed_prompts):
            print(f"  校验后移除 / Verify then remove: {filename}")
        if args.dry_run:
            print("  预览完成，未修改文件 / Dry run complete; no files changed.")
            continue
        if cfg_path.exists():
            snapshot = backup_file(cfg_path)
            print(f"  已创建恢复前备份 / Pre-reset snapshot: {snapshot.name}")
        _changed, status = restore_opencode_instructions(cfg_path)
        status_messages = {"restored": "已恢复原 instructions / Previous restored", "removed": "已移除 managed instructions / Removed", "not-managed": "当前 instructions 不属于本脚本 / Left unchanged", "missing": "config 不存在 / Not found", "unchanged": "无需修改 / No change needed"}
        print("  配置状态 / Config status:", status_messages[status])
        removed = preserved = 0
        for filename, metadata in managed_prompts.items():
            prompt_path = opencode_dir / filename
            expected_digest = metadata.get("sha256") if isinstance(metadata, dict) else None
            existed_before = metadata.get("existed_before", True) if isinstance(metadata, dict) else True
            try:
                digest_matches = not existed_before and prompt_path.is_file() and bool(expected_digest) and file_sha256(prompt_path) == expected_digest
            except OSError:
                digest_matches = False
            if digest_matches:
                prompt_path.unlink()
                removed += 1
            elif prompt_path.exists():
                preserved += 1
                reason = "部署前已存在 / pre-existing" if existed_before else "用户已修改 / user-modified"
                print(f"  已保留文件 / Preserved file ({reason}): {prompt_path.name}")
        state_path = opencode_state_file_path(cfg_path)
        if state_path.exists():
            state_path.unlink()
        print(f"  提示词状态 / Prompt status: 已移除 {removed} 个，保留 {preserved} 个 / Removed {removed}, preserved {preserved}")
    return 0

def status_report(args: argparse.Namespace) -> int:
    print(section_banner("状态 / Status"))
    # Codex
    codex_dirs = selected_codex_dirs(getattr(args, "codex_dir", None))
    if codex_dirs:
        for d in codex_dirs:
            cfg = d / "config.toml"
            print(f"\n[Codex] {d}")
            if cfg.exists():
                text = cfg.read_text(encoding="utf-8")
                line = top_level_model_instructions_line(text)
                print(f"  config.toml: {line if line else '(no model_instructions_file)'}")
                state = read_state(cfg)
                if state:
                    print(f"  state: {state['managed_prompts']}")
                    print(f"  previous: {state['previous_model_instructions_line']}")
                else:
                    print("  state: (none)")
                for fn in MANAGED_PROMPT_FILENAMES:
                    p = d / fn
                    if p.exists():
                        print(f"  file: {fn} ({p.stat().st_size} B, sha {file_sha256(p)[:12]})")
            else:
                print("  (no config.toml)")
    else:
        print("\n[Codex] (bulunamadı / not found)")

    # opencode
    opencode_dirs = selected_opencode_dirs(getattr(args, "opencode_dir", None))
    if not opencode_dirs:
        # try default
        opencode_dirs = [Path.home() / ".config" / "opencode"]
    for d in opencode_dirs:
        cfg = None
        for name in ("opencode.jsonc", "opencode.json"):
            p = d / name
            if p.exists():
                cfg = p
                break
        print(f"\n[opencode] {d}")
        if cfg and cfg.exists():
            data, _ = load_opencode_json(cfg)
            instr = get_instructions_list(data)
            print(f"  config: {cfg.name}")
            print(f"  instructions: {instr}")
            state = read_opencode_state(cfg)
            if state:
                print(f"  state: {state}")
            else:
                print("  state: (none)")
            for fn in MANAGED_PROMPT_FILENAMES:
                p = d / fn
                if p.exists():
                    print(f"  file: {fn} ({p.stat().st_size} B)")
            # also show skill existence
            skill = Path.home() / ".config" / "opencode" / "skills" / "gpt-instruct"
            if skill.exists():
                print(f"  skill: {skill} (installed)")
            else:
                print(f"  skill: (not installed at {skill})")
        else:
            print("  (no opencode.jsonc/json)")
    return 0

def interactive_action() -> str:
    print(intro_text())
    print(menu_text())
    while True:
        try:
            choice = input("请选择 / Select [1/2/3/4/5/q]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return "quit"
        actions = {"1": "apply:gpt-5.6-v45:both", "2": "apply:gpt-6-v1:both", "3": "reset:both", "4": "apply:gpt-5.6-v45:opencode", "5": "apply:gpt-5.6-v45:codex", "q": "quit"}
        if choice in actions:
            return actions[choice]
        print("[错误] 请输入 1、2、3、4、5 或 q")

def inferred_md_filename(source: Path, requested_name: str | None) -> str:
    if requested_name:
        return requested_name if requested_name.endswith(".md") else f"{requested_name}.md"
    return f"{source.stem}.md"

def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy or reset gpt-instruct prompts for Codex and opencode.")
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument("--apply", action="store_true", help="Apply a packaged instruction")
    action_group.add_argument("--reset", action="store_true", help="Remove managed prompts")
    action_group.add_argument("--status", action="store_true", help="Show current status")
    action_group.add_argument("--restore-snapshot", metavar="PATH", help="Restore full config.toml snapshot (codex only)")
    action_group.add_argument("--file", "-f", help="Apply a custom instruction ZIP or Markdown file")
    parser.add_argument("--version", choices=tuple(PROMPT_VERSIONS), help="Packaged version for --apply: gpt-5.6-v45 or gpt-6-v1")
    parser.add_argument("--target", choices=("both", "codex", "opencode"), default="both", help="Deployment target (default: both)")
    parser.add_argument("--name", "-n", help="Destination filename for --file, with or without .md")
    parser.add_argument("--codex-dir", help="Explicit Codex home directory, e.g. ~/.codex")
    parser.add_argument("--opencode-dir", help="Explicit opencode home directory, e.g. ~/.config/opencode")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt (for automation)")
    args = parser.parse_args()

    if args.name and not args.file:
        parser.error("--name 仅能与 --file 一起使用 / --name requires --file")
    if args.version and not args.apply and not args.file:
        # allow --version without --apply if interactive? but enforce
        pass

    if args.status:
        return status_report(args)
    if args.apply:
        action = f"apply:{args.version or DEFAULT_PROMPT_VERSION}:{args.target}"
    elif args.reset:
        return reset_managed_install(args)
    elif args.restore_snapshot:
        # only codex snapshot restore is supported (opencode uses json)
        from types import SimpleNamespace
        tmp = SimpleNamespace(codex_dir=args.codex_dir, dry_run=args.dry_run)
        # reuse original function
        # need to import? define inline
        # call restore_config_snapshot
        # we reimplement minimal
        snapshot = Path(args.restore_snapshot).expanduser().resolve()
        codex_dirs = selected_codex_dirs(args.codex_dir)
        if len(codex_dirs) != 1:
            print("[错误] snapshot restore requires --codex-dir", file=sys.stderr)
            return 2
        codex_dir = codex_dirs[0]
        config_path = codex_dir / "config.toml"
        allowed = {config_path.name + BASELINE_BACKUP_SUFFIX}
        valid = snapshot.name.startswith(config_path.name + ".bak_") or snapshot.name in allowed
        if snapshot.parent != codex_dir.resolve() or not snapshot.is_file() or not valid:
            print("[错误] Snapshot must be inside CODEX_HOME", file=sys.stderr)
            return 2
        snapshot_text = snapshot.read_text(encoding="utf-8")
        print(f"[+] Snapshot: {snapshot}")
        print(f"[+] Target: {config_path}")
        if args.dry_run:
            print("  Dry run complete")
            return 0
        try:
            ans = input("确认完整恢复？/ Confirm full restore? [y/N]: ").strip().lower()
        except:
            ans = "n"
        if ans not in {"y","yes","是"}:
            print("  cancelled")
            return 0
        if config_path.exists():
            backup_file(config_path)
        atomic_write_text(config_path, snapshot_text, follow_symlink=True)
        print("  restored")
        return 0
    elif args.file:
        source = Path(args.file).expanduser().resolve()
        return deploy_prompt(args, source, inferred_md_filename(source, args.name))
    else:
        action = interactive_action()

    if action == "quit":
        print("未执行修改 / No modification made.")
        return 0
    if action.startswith("reset"):
        _, tgt = action.split(":")
        args.target = tgt
        return reset_managed_install(args)
    # apply
    _, version, tgt = action.split(":")
    args.target = tgt
    # override version if specified via --version
    if args.version:
        version = args.version
    prompt_archive, prompt_md_filename = PROMPT_VERSIONS[version]
    # prompt_archive is now direct .md path, not zip
    return deploy_prompt(args, prompt_archive, prompt_md_filename)

if __name__ == "__main__":
    raise SystemExit(main())
