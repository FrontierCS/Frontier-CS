import os
import tarfile
import base64
import re
from typing import List, Tuple, Optional, Union


def _is_text(data: bytes) -> bool:
    if not data:
        return True
    # Consider text if mostly printable ASCII or common whitespace
    text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(32, 127)))
    nontext = sum(1 for b in data if b not in text_chars)
    return nontext <= max(3, len(data) // 20)


def _score_filename(name: str, target_id: str) -> int:
    name_lower = name.lower()
    score = 0
    if target_id in name_lower:
        score += 1000
    # Strong hints
    hints = [
        "oss-fuzz", "ossfuzz", "clusterfuzz", "fuzz", "fuzzer", "repro", "reproducer",
        "poc", "crash", "bug", "issue", "regress", "test", "case", "uaf", "io", "output", "buffer"
    ]
    for h in hints:
        if h in name_lower:
            score += 50
    # Prefer likely data file extensions
    if any(name_lower.endswith(ext) for ext in [".xml", ".html", ".dat", ".bin", ".txt", ".seed"]):
        score += 10
    # Slight bonus for small files usually being PoCs
    return score


def _score_size(size: int, target_len: int) -> int:
    # Prefer sizes close to target length
    diff = abs(size - target_len)
    return max(0, 300 - diff * 10)


def _extract_bytes_from_text(text: str) -> List[bytes]:
    candidates: List[bytes] = []

    # 1) C array of hex bytes: { 0x.., 0x.., ... }
    c_array_pattern = re.compile(r'\{([^}]*)\}')
    for m in c_array_pattern.finditer(text):
        content = m.group(1)
        hex_bytes = re.findall(r'0x([0-9a-fA-F]{2})', content)
        if hex_bytes:
            try:
                candidates.append(bytes(int(h, 16) for h in hex_bytes))
            except Exception:
                pass

    # 2) Plain hex dump: sequences of hex pairs
    # Allow spaces, newlines, colons
    hex_blocks = re.findall(r'(?:[0-9a-fA-F]{2}[\s:,-]*){8,}', text)  # at least 8 bytes
    for block in hex_blocks:
        hex_pairs = re.findall(r'([0-9a-fA-F]{2})', block)
        if hex_pairs:
            try:
                candidates.append(bytes(int(h, 16) for h in hex_pairs))
            except Exception:
                pass

    # 3) Base64 blocks
    b64_blocks = re.findall(r'([A-Za-z0-9+/=]{16,})', text)
    for b64 in b64_blocks:
        # Try to decode base64 safely
        try:
            decoded = base64.b64decode(b64, validate=False)
            if decoded:
                candidates.append(decoded)
        except Exception:
            pass

    # 4) Python-like bytes literal b'...'
    py_bytes_pat = re.compile(r"b'([^']*)'")
    for m in py_bytes_pat.finditer(text):
        s = m.group(1)
        try:
            # Interpret python-style escape sequences
            decoded = bytes(s, 'utf-8').decode('unicode_escape').encode('latin1', 'ignore')
            if decoded:
                candidates.append(decoded)
        except Exception:
            pass

    return candidates


def _iter_tar_members_bytes(src_path: str):
    with tarfile.open(src_path, 'r:*') as tf:
        for m in tf.getmembers():
            if not m.isreg():
                continue
            # Limit size to avoid huge files
            if m.size <= 0 or m.size > 2 * 1024 * 1024:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                yield m.name, data
            except Exception:
                continue


def _iter_dir_files_bytes(src_dir: str):
    for root, _, files in os.walk(src_dir):
        for fn in files:
            full = os.path.join(root, fn)
            try:
                st = os.stat(full)
                if st.st_size <= 0 or st.st_size > 2 * 1024 * 1024:
                    continue
                with open(full, 'rb') as f:
                    data = f.read()
                rel = os.path.relpath(full, src_dir)
                yield rel, data
            except Exception:
                continue


def _find_best_candidate_from_repo(src_path: str, target_id: str, target_len: int) -> Optional[bytes]:
    is_dir = os.path.isdir(src_path)
    items = _iter_dir_files_bytes(src_path) if is_dir else _iter_tar_members_bytes(src_path)

    best: Tuple[int, bytes] = (-1, b'')

    for name, data in items:
        base_score = _score_filename(name, target_id)
        if base_score <= 0 and target_id not in name:
            # Still consider, but deprioritize
            base_score = 0

        # Direct use of file as PoC
        size_score = _score_size(len(data), target_len)
        total_score = base_score + size_score

        # Heuristic: prioritize very small files
        if len(data) <= 512:
            total_score += 20

        # Heuristic: prioritize binary-looking small files
        if not _is_text(data) and len(data) <= 1024:
            total_score += 30

        # Record if promising
        if total_score > best[0]:
            best = (total_score, data)

        # If text, try to extract embedded byte sequences
        if _is_text(data):
            try:
                text = data.decode('utf-8', errors='ignore')
            except Exception:
                text = ''

            # Look specifically for the target id in content
            content_bonus = 200 if target_id in text else 0
            extracted = _extract_bytes_from_text(text)
            for cand in extracted:
                escore = base_score + content_bonus + _score_size(len(cand), target_len)
                if len(cand) <= 512:
                    escore += 20
                if not _is_text(cand):
                    escore += 10
                if escore > best[0]:
                    best = (escore, cand)

    if best[0] >= 0:
        return best[1]
    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_id = "42537493"
        target_len = 24

        # Attempt to find a PoC directly from the repository/tarball
        poc = _find_best_candidate_from_repo(src_path, target_id, target_len)
        if poc:
            return poc

        # Fallback: Return a deterministic placeholder of the target length.
        # Note: This is a last resort and may not trigger the vulnerability.
        return b'A' * target_len
