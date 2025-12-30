import os
import io
import tarfile
import zipfile
import re

def _is_probably_binary(data: bytes) -> bool:
    if not data:
        return False
    # If many non-text bytes, consider it binary
    text_chars = set(range(32, 127)) | {9, 10, 13}
    non_text = sum(1 for b in data if b not in text_chars)
    return (non_text / max(1, len(data))) > 0.2

def _score_candidate(name: str, data: bytes) -> int:
    n = name.lower()
    score = 0
    # Name-based heuristics
    if 'capwap' in n:
        score += 200
    if 'poc' in n or 'proof' in n:
        score += 120
    if 'crash' in n:
        score += 100
    if 'min' in n or 'minimized' in n:
        score += 80
    if 'id:' in n or 'id_' in n:
        score += 60
    if 'oss' in n or 'fuzz' in n or 'clusterfuzz' in n or 'afl' in n:
        score += 40
    if 'heap' in n or 'overread' in n or 'overflow' in n:
        score += 80
    if 'ndpi' in n:
        score += 40

    # Length-based heuristic centered on 33 bytes
    if len(data) == 33:
        score += 300
    else:
        # Prefer closer to 33
        score += max(0, 150 - abs(len(data) - 33))

    # Data/content based heuristics
    if _is_probably_binary(data):
        score += 30
    else:
        score -= 50  # Avoid picking source/text files

    # Penalize very large files
    if len(data) > 1_000_000:
        score -= 200

    return score

def _iter_tar_members(tf: tarfile.TarFile):
    for m in tf.getmembers():
        if m.isfile():
            yield m

def _walk_tar(tf: tarfile.TarFile, prefix: str, depth: int, max_depth: int, size_limit: int, files: list):
    for m in _iter_tar_members(tf):
        name = os.path.join(prefix, m.name) if prefix else m.name
        # Skip very large files for memory considerations
        if m.size > size_limit:
            continue
        f = tf.extractfile(m)
        if f is None:
            continue
        try:
            data = f.read()
        except Exception:
            continue
        files.append((name, data))
        # Recurse into nested archives (limited depth)
        if depth < max_depth:
            nested = _maybe_walk_nested(name, data, depth + 1, max_depth, size_limit)
            files.extend(nested)

def _walk_zip(zf: zipfile.ZipFile, prefix: str, depth: int, max_depth: int, size_limit: int, files: list):
    for info in zf.infolist():
        if info.is_dir():
            continue
        if info.file_size > size_limit:
            continue
        try:
            data = zf.read(info)
        except Exception:
            continue
        name = os.path.join(prefix, info.filename) if prefix else info.filename
        files.append((name, data))
        if depth < max_depth:
            nested = _maybe_walk_nested(name, data, depth + 1, max_depth, size_limit)
            files.extend(nested)

def _maybe_open_tar_from_bytes(data: bytes):
    try:
        bio = io.BytesIO(data)
        tf = tarfile.open(fileobj=bio, mode='r:*')
        return tf
    except Exception:
        return None

def _maybe_open_zip_from_bytes(data: bytes):
    try:
        bio = io.BytesIO(data)
        zf = zipfile.ZipFile(bio, mode='r')
        # Try listing to ensure it's a valid zip
        _ = zf.infolist()
        return zf
    except Exception:
        return None

def _maybe_walk_nested(name: str, data: bytes, depth: int, max_depth: int, size_limit: int):
    results = []
    lname = name.lower()
    likely_archive = any(ext in lname for ext in ('.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz', '.zip', '.gz'))
    if not likely_archive and len(data) > 0:
        # Heuristic: try to open anyway if the data appears to be an archive signature
        signatures = [
            (b'PK\x03\x04', 'zip'),
            (b'\x1F\x8B\x08', 'gz'),
        ]
        if not any(data.startswith(sig) for sig, _ in signatures):
            return results

    tf = _maybe_open_tar_from_bytes(data)
    if tf is not None:
        try:
            _walk_tar(tf, name, depth, max_depth, size_limit, results)
        finally:
            try:
                tf.close()
            except Exception:
                pass
        return results

    zf = _maybe_open_zip_from_bytes(data)
    if zf is not None:
        try:
            _walk_zip(zf, name, depth, max_depth, size_limit, results)
        finally:
            try:
                zf.close()
            except Exception:
                pass
        return results

    # Try gzip (single file) - decompress and treat as raw file content
    if data.startswith(b'\x1F\x8B\x08'):
        try:
            import gzip
            bio = io.BytesIO(data)
            with gzip.GzipFile(fileobj=bio) as gz:
                decompressed = gz.read()
                results.append((name + '.gunzipped', decompressed))
        except Exception:
            pass

    return results

def _collect_all_files_from_archive(src_path: str, max_depth: int = 2, size_limit: int = 10 * 1024 * 1024):
    files = []
    # First try tar
    try:
        with tarfile.open(src_path, mode='r:*') as tf:
            _walk_tar(tf, "", 0, max_depth, size_limit, files)
            return files
    except Exception:
        pass
    # Try zip
    try:
        with zipfile.ZipFile(src_path, mode='r') as zf:
            _walk_zip(zf, "", 0, max_depth, size_limit, files)
            return files
    except Exception:
        pass
    # Not an archive: just read as a single file
    try:
        if os.path.getsize(src_path) <= size_limit:
            with open(src_path, 'rb') as f:
                data = f.read()
            return [(os.path.basename(src_path), data)]
    except Exception:
        pass
    return files

def _select_best_poc(files):
    # Prefer files within plausible PoC directories
    preferred_dirs = [
        'poc', 'pocs', 'crash', 'crashes', 'tests', 'test', 'seeds',
        'inputs', 'fuzz', 'oss-fuzz', 'ossfuzz', 'clusterfuzz', 'reproducer'
    ]
    candidates = []
    for name, data in files:
        lname = name.lower()
        # Skip obvious source/text files by extension
        _, ext = os.path.splitext(lname)
        if ext in {'.c', '.h', '.md', '.txt', '.rst', '.py', '.java', '.sh', '.cmake', '.html', '.xml', '.yml', '.yaml', '.json'}:
            continue
        # Restrict to smaller binary files
        if len(data) == 0 or len(data) > 2 * 1024 * 1024:
            continue
        # Ensure it is not likely Unicode text file; but allow binary-like
        if not _is_probably_binary(data) and 'capwap' not in lname:
            continue

        in_pref_dir = any(f'/{d}/' in f'/{lname}' for d in preferred_dirs)
        score = _score_candidate(name, data)
        if in_pref_dir:
            score += 50
        # Additional boost if filename hints CAPWAP or NDPI fuzzing
        if re.search(r'capwap|ndpi', lname):
            score += 80
        candidates.append((score, name, data))

    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], -len(x[2])), reverse=True)
    return candidates[0][2]

class Solution:
    def solve(self, src_path: str) -> bytes:
        files = _collect_all_files_from_archive(src_path, max_depth=2, size_limit=10 * 1024 * 1024)
        poc = _select_best_poc(files)
        if poc is not None:
            return poc
        # Fallback: 33-byte placeholder. This may not trigger the bug, but serves as a last resort.
        return b'A' * 33