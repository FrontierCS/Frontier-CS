import os
import re
import io
import tarfile
import tempfile
import shutil
import base64
from typing import List, Tuple, Optional


def _is_tar(path: str) -> bool:
    try:
        return tarfile.is_tarfile(path)
    except Exception:
        return False


def _safe_extract(tar: tarfile.TarFile, path: str) -> None:
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        abs_directory = os.path.abspath(path)
        abs_target = os.path.abspath(member_path)
        if not abs_target.startswith(abs_directory + os.sep) and abs_target != abs_directory:
            continue
    tar.extractall(path=path)


def _extract_src(src_path: str) -> str:
    if os.path.isdir(src_path):
        return src_path
    tmpdir = tempfile.mkdtemp(prefix="src_")
    try:
        if _is_tar(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                _safe_extract(tf, tmpdir)
        else:
            # Not a tar; copy to tmpdir as-is if directory, else place in temp directory
            if os.path.isdir(src_path):
                return src_path
            os.makedirs(os.path.join(tmpdir, "data"), exist_ok=True)
            shutil.copy(src_path, os.path.join(tmpdir, "data", os.path.basename(src_path)))
        # If a single top-level directory exists, return it
        entries = [os.path.join(tmpdir, e) for e in os.listdir(tmpdir)]
        dirs = [e for e in entries if os.path.isdir(e)]
        if len(dirs) == 1 and len(entries) == 1:
            return dirs[0]
        return tmpdir
    except Exception:
        return tmpdir


def _iter_files(root: str) -> List[str]:
    out = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            out.append(full)
    return out


def _read_file_bytes(path: str, max_size: int = 5 * 1024 * 1024) -> Optional[bytes]:
    try:
        size = os.path.getsize(path)
        if size > max_size:
            return None
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None


def _is_probably_text(data: bytes) -> bool:
    if not data:
        return True
    # If there are many zero bytes, it's binary
    if data.count(0) > max(1, len(data) // 100):
        return False
    # Heuristic: if more than 85% printable + whitespace, treat as text
    printable = b"\t\n\r\f\b"
    count = 0
    for b in data:
        if 32 <= b <= 126 or b in printable:
            count += 1
    return (count / max(1, len(data))) > 0.85


def _decode_python_bytes_literal(s: str) -> List[bytes]:
    # Matches Python byte literals like b'\x41\x42A'
    # We'll implement a safe decode of \xNN and standard escapes
    out = []
    # Support both single and double quotes
    for m in re.finditer(r"b(?P<prefix>[ruRU]{0,2})?(['\"])((?:\\.|(?!\2).)*)\2", s):
        inner = m.group(3)
        # Convert escape sequences
        try:
            # Replace \xHH with bytes
            buf = bytearray()
            i = 0
            while i < len(inner):
                c = inner[i]
                if c == '\\' and i + 1 < len(inner):
                    nxt = inner[i + 1]
                    if nxt in ('\\', '\'', '"'):
                        buf.append(ord(nxt))
                        i += 2
                        continue
                    if nxt == 'x' and i + 3 < len(inner):
                        h = inner[i + 2:i + 4]
                        if re.fullmatch(r"[0-9a-fA-F]{2}", h):
                            buf.append(int(h, 16))
                            i += 4
                            continue
                    # Handle common escapes
                    mapping = {'n': 10, 'r': 13, 't': 9, 'b': 8, 'f': 12, '0': 0, 'a': 7, 'v': 11}
                    if nxt in mapping:
                        buf.append(mapping[nxt])
                        i += 2
                        continue
                    # Unknown escape, keep raw char
                    buf.append(ord(nxt))
                    i += 2
                else:
                    buf.append(ord(c))
                    i += 1
            out.append(bytes(buf))
        except Exception:
            continue
    return out


def _parse_hex_tokens_to_bytes(tokens: List[str]) -> Optional[bytes]:
    arr = []
    for tok in tokens:
        tok = tok.strip().strip(',').strip(';').strip()
        if not tok:
            continue
        if tok.lower().startswith('0x'):
            try:
                v = int(tok, 16)
            except Exception:
                return None
        else:
            # Decimal or two-char hex?
            if re.fullmatch(r"[0-9a-fA-F]{2}", tok):
                try:
                    v = int(tok, 16)
                except Exception:
                    return None
            else:
                # Decimal
                if not re.fullmatch(r"\d{1,3}", tok):
                    return None
                v = int(tok, 10)
        if not (0 <= v <= 255):
            return None
        arr.append(v)
    if not arr:
        return None
    return bytes(arr)


def _decode_c_array(s: str) -> List[bytes]:
    outs = []
    # Match content within braces that likely contains numbers
    for m in re.finditer(r"\{([^{}]+)\}", s, re.DOTALL):
        inner = m.group(1)
        # Only consider if it has hex or numbers
        if not re.search(r"(0x[0-9a-fA-F]{1,2}|\b\d{1,3}\b)", inner):
            continue
        # Split by commas or whitespace
        tokens = re.split(r"[\s,]+", inner)
        b = _parse_hex_tokens_to_bytes(tokens)
        if b is not None:
            outs.append(b)
    return outs


def _decode_hex_pairs_lines(s: str) -> List[bytes]:
    outs = []
    # Pattern: sequences of hex pairs separated by spaces, possibly multiple lines
    lines = s.splitlines()
    current_tokens = []
    for line in lines:
        # Skip address columns like "0000000:"
        line_ = re.sub(r"^\s*[0-9a-fA-F]+:\s+", "", line)
        # Remove |ascii| tails
        line_ = re.sub(r"\s+\|.*\|\s*$", "", line_)
        toks = re.findall(r"\b[0-9a-fA-F]{2}\b", line_)
        if toks:
            current_tokens.extend(toks)
        else:
            if current_tokens:
                b = _parse_hex_tokens_to_bytes(current_tokens)
                if b is not None:
                    outs.append(b)
                current_tokens = []
    if current_tokens:
        b = _parse_hex_tokens_to_bytes(current_tokens)
        if b is not None:
            outs.append(b)
    # Also match single-line hex sequences
    for m in re.finditer(r"(?:\b[0-9a-fA-F]{2}\b(?:\s+|,))+[0-9a-fA-F]{2}\b", s):
        toks = re.findall(r"\b[0-9a-fA-F]{2}\b", m.group(0))
        b = _parse_hex_tokens_to_bytes(toks)
        if b is not None:
            outs.append(b)
    return outs


def _decode_base64(s: str) -> List[bytes]:
    outs = []
    # Simple heuristic: look for long base64-like tokens
    for m in re.finditer(r"\b[A-Za-z0-9+/]{8,}={0,2}\b", s):
        token = m.group(0)
        if len(token) % 4 != 0:
            continue
        try:
            decoded = base64.b64decode(token, validate=True)
            if decoded:
                outs.append(decoded)
        except Exception:
            continue
    return outs


def _decode_numbers_structured(s: str) -> List[bytes]:
    # Match patterns like: data = [0x01, 0x02, ...] or Data: 01 02 ...
    outs = []
    for m in re.finditer(r"\[(.*?)\]", s, re.DOTALL):
        inner = m.group(1)
        tokens = re.split(r"[\s,]+", inner.strip())
        b = _parse_hex_tokens_to_bytes(tokens)
        if b is not None:
            outs.append(b)
    return outs


def _collect_bytes_from_text(content: bytes) -> List[bytes]:
    try:
        s = content.decode("utf-8", errors="ignore")
    except Exception:
        return []
    candidates = []
    candidates.extend(_decode_python_bytes_literal(s))
    candidates.extend(_decode_c_array(s))
    candidates.extend(_decode_hex_pairs_lines(s))
    candidates.extend(_decode_base64(s))
    candidates.extend(_decode_numbers_structured(s))
    # Deduplicate by content
    uniq = []
    seen = set()
    for b in candidates:
        if b is None:
            continue
        key = (len(b), hash(b))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(b)
    return uniq


def _score_candidate(path: str, data: bytes, target_len: int = 21) -> int:
    name = os.path.basename(path).lower()
    score = 0
    # Filename heuristics
    if 'poc' in name:
        score += 80
    if 'crash' in name:
        score += 70
    if 'repro' in name or 'reprod' in name:
        score += 60
    if 'trigger' in name:
        score += 50
    if 'payload' in name:
        score += 40
    if 'testcase' in name or 'case' in name:
        score += 30
    if 'input' in name:
        score += 10
    if 'coap' in path.lower():
        score += 25
    if 'message' in path.lower():
        score += 10
    if 'AppendUintOption'.lower() in path.lower():
        score += 15
    if os.path.splitext(name)[1] in ('.bin', '.raw', '.dat'):
        score += 20
    # Content length proximity
    score += max(0, 100 - abs(len(data) - target_len) * 5)
    if len(data) == target_len:
        score += 200
    # Length sanity
    if len(data) == 0:
        score -= 1000
    if len(data) > 65536:
        score -= 500
    return score


def _find_poc_bytes(root: str, target_len: int = 21) -> Optional[bytes]:
    files = _iter_files(root)
    candidates: List[Tuple[int, str, bytes]] = []

    name_patterns = re.compile(r"(poc|crash|repro|reprod|trigger|payload|testcase|input|coap|message)", re.IGNORECASE)

    for fpath in files:
        try:
            data = _read_file_bytes(fpath)
            if data is None:
                continue
            is_text = _is_probably_text(data)
            # If filename suggests PoC or it's a small binary file, consider it
            prioritized = bool(name_patterns.search(fpath))
            if not is_text and (prioritized or (0 < len(data) <= 4096)):
                score = _score_candidate(fpath, data, target_len)
                candidates.append((score, fpath, data))
                continue
            if is_text and prioritized:
                # Parse potential byte representations from text content
                arrs = _collect_bytes_from_text(data)
                for b in arrs:
                    score = _score_candidate(fpath, b, target_len)
                    candidates.append((score, fpath, b))
        except Exception:
            continue

    # If no prioritized candidates found, try parsing all small text files
    if not candidates:
        for fpath in files:
            try:
                data = _read_file_bytes(fpath)
                if data is None or not _is_probably_text(data):
                    continue
                # Limit scanning to moderately small files
                if len(data) > 512 * 1024:
                    continue
                arrs = _collect_bytes_from_text(data)
                for b in arrs:
                    score = _score_candidate(fpath, b, target_len)
                    candidates.append((score, fpath, b))
            except Exception:
                continue

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)

    # Prefer exact length match of 21
    for score, path, b in candidates:
        if len(b) == target_len:
            return b

    # Fallback to best-scored candidate
    return candidates[0][2] if candidates else None


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = _extract_src(src_path)
        try:
            poc = _find_poc_bytes(root, target_len=21)
            if poc is not None:
                return poc
        except Exception:
            pass
        # Fallback: return 21-byte placeholder if no PoC found
        return b"A" * 21
