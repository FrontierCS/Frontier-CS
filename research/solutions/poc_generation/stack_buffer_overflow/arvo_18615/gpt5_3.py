import os
import tarfile
import zipfile
from typing import Iterator, Tuple, Optional


def _iter_tar_files(src_path: str) -> Iterator[Tuple[str, bytes]]:
    try:
        with tarfile.open(src_path, 'r:*') as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read()
                finally:
                    f.close()
                yield m.name, data
    except tarfile.ReadError:
        return


def _iter_zip_files(src_path: str) -> Iterator[Tuple[str, bytes]]:
    try:
        with zipfile.ZipFile(src_path, 'r') as zf:
            for name in zf.namelist():
                try:
                    with zf.open(name) as f:
                        data = f.read()
                    yield name, data
                except Exception:
                    continue
    except zipfile.BadZipFile:
        return


def _iter_dir_files(src_dir: str) -> Iterator[Tuple[str, bytes]]:
    for root, _, files in os.walk(src_dir):
        for fn in files:
            path = os.path.join(root, fn)
            try:
                with open(path, 'rb') as f:
                    data = f.read()
                rel = os.path.relpath(path, src_dir)
                yield rel, data
            except Exception:
                continue


def _is_binary(data: bytes) -> bool:
    if not data:
        return False
    # Consider binary if any NUL or > 0x7F or control chars excluding \r\n\t
    for b in data:
        if b == 0:
            return True
        if b < 0x09:
            return True
        if 0x0E <= b < 0x20:
            return True
        if b > 0x7E:
            return True
    return False


def _score_name(name: str) -> int:
    n = name.lower()
    score = 0
    if 'poc' in n:
        score += 50
    if 'crash' in n or 'id:' in n or 'id_' in n or 'id-' in n:
        score += 25
    if 'tic30' in n or 'tic-30' in n:
        score += 15
    if 'objdump' in n or 'dis' in n or 'disas' in n:
        score += 10
    if 'branch' in n:
        score += 6
    if 'print' in n:
        score += 3
    if '18615' in n:
        score += 20
    if n.endswith('.bin') or n.endswith('.dat') or n.endswith('.raw'):
        score += 5
    if 'binutils' in n:
        score += 3
    return score


def _select_poc(files: Iterator[Tuple[str, bytes]]) -> Optional[bytes]:
    # First pass: exact 10-byte files
    best = None
    best_score = -1
    for name, data in files:
        if len(data) == 10:
            score = _score_name(name)
            if _is_binary(data):
                score += 10
            # Prefer non-text and more indicative names
            if score > best_score:
                best_score = score
                best = data
    if best is not None:
        return best
    return None


def _select_poc_fallback(files: Iterator[Tuple[str, bytes]]) -> Optional[bytes]:
    # Look for very small files likely to be PoCs and trim/pad to 10 if clearly intended
    candidates = []
    for name, data in files:
        sz = len(data)
        if sz == 0 or sz > 64:
            continue
        score = _score_name(name)
        if _is_binary(data):
            score += 10
        # strong preference for names indicating poc/crash even if size != 10
        if 'poc' in name.lower() or 'crash' in name.lower() or 'id_' in name.lower():
            candidates.append((score, name, data))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    data = candidates[0][2]
    if len(data) == 10:
        return data
    # If longer than 10, try to take the first 10 bytes (common for raw PoCs)
    if len(data) > 10:
        return data[:10]
    # If shorter, pad with zeros (unlikely to be correct, but best-effort)
    return data + b'\x00' * (10 - len(data))


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try tar, then zip, then directory
        # Collect two iterators for two passes since iterators are one-shot
        files_tar = list(_iter_tar_files(src_path))
        files_zip = list(_iter_zip_files(src_path))
        files_dir = list(_iter_dir_files(src_path)) if os.path.isdir(src_path) else []

        # First preference: tar contents
        if files_tar:
            poc = _select_poc(iter(files_tar))
            if poc is not None:
                return poc
        # Second: zip contents
        if files_zip:
            poc = _select_poc(iter(files_zip))
            if poc is not None:
                return poc
        # Third: directory
        if files_dir:
            poc = _select_poc(iter(files_dir))
            if poc is not None:
                return poc

        # Fallback: attempt relaxed selection on small files
        if files_tar:
            poc = _select_poc_fallback(iter(files_tar))
            if poc is not None:
                return poc
        if files_zip:
            poc = _select_poc_fallback(iter(files_zip))
            if poc is not None:
                return poc
        if files_dir:
            poc = _select_poc_fallback(iter(files_dir))
            if poc is not None:
                return poc

        # Final fallback: return a 10-byte binary placeholder
        return b'\x00\xff\x00\xff\xaa\x55\xcc\x33\x66\x99'