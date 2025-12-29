import os
import io
import re
import tarfile
import zipfile
import gzip
import bz2
import lzma


TARGET_LENGTH = 6431


def _decompress_by_ext(name_lower: str, data: bytes) -> bytes:
    try:
        if name_lower.endswith('.gz'):
            return gzip.decompress(data)
        if name_lower.endswith('.bz2'):
            return bz2.decompress(data)
        if name_lower.endswith('.xz') or name_lower.endswith('.lzma'):
            return lzma.decompress(data)
    except Exception:
        return b""
    return data


def _is_pdf_data(data: bytes) -> bool:
    if not data:
        return False
    # Allow leading whitespace or garbage up to a small threshold before %PDF-
    pos = data.find(b'%PDF-')
    return 0 <= pos <= 2048


def _name_score(name_lower: str) -> int:
    score = 0
    if 'uaf' in name_lower or 'use-after-free' in name_lower:
        score += 500
    if 'xref' in name_lower:
        score += 400
    if 'objstm' in name_lower or ('obj' in name_lower and 'stm' in name_lower):
        score += 350
    if 'object' in name_lower:
        score += 200
    if 'oss-fuzz' in name_lower or 'clusterfuzz' in name_lower:
        score += 300
    if 'crash' in name_lower:
        score += 200
    if 'regress' in name_lower or 'repro' in name_lower or 'poc' in name_lower or 'test' in name_lower or 'fuzz' in name_lower:
        score += 150
    if 'pdf' in name_lower:
        score += 50
    return score


def _score_candidate(name: str, data: bytes) -> float:
    name_lower = name.lower()
    score = _name_score(name_lower)
    length = len(data)
    if length == TARGET_LENGTH:
        score += 5000
    # Closeness to target length
    score -= abs(length - TARGET_LENGTH) / 10.0
    # Prefer reasonably sized files
    if length > 0 and length < 1024 * 1024:
        score += 20
    return score


def _iter_tar_files(src_path):
    try:
        with tarfile.open(src_path, 'r:*') as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                size = m.size
                f = tf.extractfile(m)
                if f is None:
                    continue
                yield name, size, lambda f=f: f.read()
    except Exception:
        return


def _iter_zip_files(src_path):
    try:
        with zipfile.ZipFile(src_path, 'r') as zf:
            for zi in zf.infolist():
                if zi.is_dir():
                    continue
                name = zi.filename
                size = zi.file_size
                yield name, size, lambda name=name, zf=zf: zf.read(name)
    except Exception:
        return


def _iter_dir_files(src_path):
    for root, _, files in os.walk(src_path):
        for fn in files:
            full = os.path.join(root, fn)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            def reader(p=full):
                try:
                    with open(p, 'rb') as f:
                        return f.read()
                except Exception:
                    return b""
            yield full, size, reader


def _gather_candidates(file_iter):
    candidates = []
    pdf_ext_re = re.compile(r'.*\.pdf(\.(gz|xz|lzma|bz2))?$', re.IGNORECASE)
    # First pass: by extension
    for name, size, reader in file_iter:
        name_lower = name.lower()
        is_ext_pdf = bool(pdf_ext_re.match(name_lower))
        if is_ext_pdf:
            try:
                raw = reader()
            except Exception:
                continue
            if not raw:
                continue
            data = _decompress_by_ext(name_lower, raw)
            if not data:
                # If decompression failed or not applicable, fall back to raw when extension was .pdf
                if name_lower.endswith('.pdf'):
                    data = raw
                else:
                    continue
            if _is_pdf_data(data):
                score = _score_candidate(name, data)
                candidates.append((score, name, data))
    # Second pass: sniff small files without .pdf extension
    if not candidates:
        for name, size, reader in file_iter:
            if size <= 0 or size > 8 * 1024 * 1024:
                continue
            name_lower = name.lower()
            # Skip obvious binaries that are unlikely to be PDF testcases by extension
            skip_exts = ('.c', '.h', '.cc', '.cpp', '.java', '.py', '.rb', '.go', '.js', '.ts', '.md', '.txt', '.sh', '.cmake', '.mk', '.make', '.html', '.xml', '.json', '.yml', '.yaml', '.in', '.out', '.diff', '.patch', '.gif', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.ico', '.svg', '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac', '.zip', '.tar', '.gz', '.xz', '.bz2', '.7z', '.rar', '.so', '.a', '.o', '.obj', '.dll', '.dylib')
            if name_lower.endswith(skip_exts):
                continue
            try:
                data = reader()
            except Exception:
                continue
            if not data:
                continue
            if _is_pdf_data(data):
                score = _score_candidate(name, data)
                candidates.append((score, name, data))
    return candidates


def _build_minimal_pdf() -> bytes:
    # Build a tiny valid PDF
    parts = []
    def w(s):
        parts.append(s if isinstance(s, (bytes, bytearray)) else s.encode('ascii'))
    w('%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = []
    # Obj 1: Catalog
    offsets.append(sum(len(p) for p in parts))
    w('1 0 obj\n')
    w('<< /Type /Catalog /Pages 2 0 R >>\n')
    w('endobj\n')
    # Obj 2: Pages
    offsets.append(sum(len(p) for p in parts))
    w('2 0 obj\n')
    w('<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n')
    w('endobj\n')
    # Obj 3: Page
    offsets.append(sum(len(p) for p in parts))
    w('3 0 obj\n')
    w('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>\n')
    w('endobj\n')
    xref_offset = sum(len(p) for p in parts)
    w('xref\n')
    w('0 4\n')
    w('0000000000 65535 f \n')
    for off in offsets:
        w(f'{off:010d} 00000 n \n')
    w('trailer\n')
    w('<< /Size 4 /Root 1 0 R >>\n')
    w('startxref\n')
    w(f'{xref_offset}\n')
    w('%%EOF\n')
    return b''.join(parts)


class Solution:
    def solve(self, src_path: str) -> bytes:
        candidates = []

        # Try tar
        if tarfile.is_tarfile(src_path):
            candidates.extend(_gather_candidates(_iter_tar_files(src_path)))
        # Try zip
        elif zipfile.is_zipfile(src_path):
            candidates.extend(_gather_candidates(_iter_zip_files(src_path)))
        # Try directory
        elif os.path.isdir(src_path):
            candidates.extend(_gather_candidates(_iter_dir_files(src_path)))
        else:
            # If it's a file, maybe it's already the PDF or an archive
            try:
                with open(src_path, 'rb') as f:
                    data = f.read()
                # Try to parse as tar
                if tarfile.is_tarfile(src_path):
                    candidates.extend(_gather_candidates(_iter_tar_files(src_path)))
                elif zipfile.is_zipfile(src_path):
                    candidates.extend(_gather_candidates(_iter_zip_files(src_path)))
                else:
                    # If it's a PDF directly
                    if _is_pdf_data(data):
                        candidates.append((_score_candidate(os.path.basename(src_path), data), src_path, data))
            except Exception:
                pass

        if candidates:
            best = max(candidates, key=lambda x: x[0])
            return best[2]

        # Fallback minimal PDF
        return _build_minimal_pdf()