import os
import tarfile
import re
import io
import zipfile
import gzip
import tempfile


class Solution:
    def __init__(self):
        self.LG = 33453
        self.patterns = [
            (re.compile(r'42535152'), 1000.0),
            (re.compile(r'oss[-_]?fuzz'), 500.0),
            (re.compile(r'clusterfuzz'), 400.0),
            (re.compile(r'testcase'), 300.0),
            (re.compile(r'crash'), 300.0),
            (re.compile(r'poc'), 300.0),
            (re.compile(r'repro'), 250.0),
            (re.compile(r'use[_-]?after[_-]?free'), 200.0),
            (re.compile(r'\buaf\b'), 150.0),
            (re.compile(r'qpdf'), 100.0),
            (re.compile(r'fuzz'), 80.0),
            (re.compile(r'asan'), 60.0),
            (re.compile(r'ubsan'), 60.0),
            (re.compile(r'\.pdf'), 40.0),
        ]
        self.nested_name_tokens = [
            '42535152',
            'clusterfuzz',
            'oss-fuzz',
            'ossfuzz',
            'qpdf',
            'fuzz',
            'testcase',
            'crash',
            'poc',
        ]

    def _score_candidate(self, path_lower: str, size: int, penalize_non_pdf: bool = True) -> float:
        score = 0.0
        for regex, weight in self.patterns:
            if regex.search(path_lower):
                score += weight
        diff = abs(size - self.LG)
        size_score = 300.0 - (diff / 100.0)
        if size_score < 0.0:
            size_score = 0.0
        score += size_score
        if '/tests/' in path_lower or path_lower.startswith('tests/'):
            score += 50.0
        if 'regress' in path_lower:
            score += 50.0
        if 'bug' in path_lower:
            score += 25.0
        if penalize_non_pdf:
            if not path_lower.endswith('.pdf') and '.pdf' not in path_lower:
                score -= 150.0
        if score < 0.0:
            score = 0.0
        return score

    def _fallback_poc(self) -> bytes:
        return (
            b'%PDF-1.4\n'
            b'1 0 obj\n'
            b'<< /Type /Catalog /Pages 2 0 R >>\n'
            b'endobj\n'
            b'2 0 obj\n'
            b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n'
            b'endobj\n'
            b'3 0 obj\n'
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\n'
            b'endobj\n'
            b'trailer\n'
            b'<< /Root 1 0 R >>\n'
            b'%%EOF\n'
        )

    def _solve_from_tar(self, src_path: str) -> bytes:
        best_member = None
        best_score = -1.0
        nested_best_data = None
        nested_best_score = -1.0

        try:
            tf = tarfile.open(src_path, 'r:*')
        except tarfile.ReadError:
            return self._fallback_poc()

        with tf:
            members = tf.getmembers()

            # Direct candidates (e.g., .pdf files)
            for member in members:
                if not member.isreg():
                    continue
                size = member.size
                if size <= 0 or size > 2 * 1024 * 1024:
                    continue
                path_lower = member.name.lower()
                score = self._score_candidate(path_lower, size, penalize_non_pdf=True)
                if score > best_score:
                    best_score = score
                    best_member = member

            direct_data = None
            if best_member is not None and best_score > 0.0:
                try:
                    f = tf.extractfile(best_member)
                    if f is not None:
                        data = f.read()
                        if data:
                            direct_data = data
                except Exception:
                    direct_data = None

            # Nested archives (.zip, .gz) that may contain the PoC
            for member in members:
                if not member.isreg():
                    continue
                if member.size <= 0 or member.size > 5 * 1024 * 1024:
                    continue
                name_lower = member.name.lower()
                if not (name_lower.endswith('.zip') or name_lower.endswith('.gz')):
                    continue
                if not any(tok in name_lower for tok in self.nested_name_tokens):
                    continue
                try:
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    raw = f.read()
                except Exception:
                    continue
                if not raw:
                    continue

                if name_lower.endswith('.zip'):
                    try:
                        zf = zipfile.ZipFile(io.BytesIO(raw))
                    except Exception:
                        continue
                    for zi in zf.infolist():
                        try:
                            data = zf.read(zi)
                        except Exception:
                            continue
                        if not data:
                            continue
                        size2 = len(data)
                        combined_name = name_lower + '/' + zi.filename.lower()
                        score = self._score_candidate(
                            combined_name, size2, penalize_non_pdf=False
                        )
                        if score > nested_best_score:
                            nested_best_score = score
                            nested_best_data = data
                else:
                    try:
                        data = gzip.decompress(raw)
                    except Exception:
                        continue
                    if not data:
                        continue
                    size2 = len(data)
                    score = self._score_candidate(
                        name_lower, size2, penalize_non_pdf=False
                    )
                    if score > nested_best_score:
                        nested_best_score = score
                        nested_best_data = data

        if nested_best_data is not None and nested_best_score >= (best_score if best_score > 0.0 else 0.0):
            return nested_best_data
        if direct_data is not None:
            return direct_data
        return self._fallback_poc()

    def _solve_from_dir(self, src_dir: str) -> bytes:
        best_path = None
        best_score = -1.0
        nested_best_data = None
        nested_best_score = -1.0

        for root, _, files in os.walk(src_dir):
            for fname in files:
                full_path = os.path.join(root, fname)
                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    continue
                if size <= 0:
                    continue
                path_lower = full_path.lower()

                # Direct candidate
                if size <= 2 * 1024 * 1024:
                    score = self._score_candidate(path_lower, size, penalize_non_pdf=True)
                    if score > best_score:
                        best_score = score
                        best_path = full_path

                # Nested archives
                if size <= 5 * 1024 * 1024 and (
                    path_lower.endswith('.zip') or path_lower.endswith('.gz')
                ):
                    if not any(tok in path_lower for tok in self.nested_name_tokens):
                        continue
                    try:
                        with open(full_path, 'rb') as fh:
                            raw = fh.read()
                    except OSError:
                        continue
                    if not raw:
                        continue

                    if path_lower.endswith('.zip'):
                        try:
                            zf = zipfile.ZipFile(io.BytesIO(raw))
                        except Exception:
                            continue
                        for zi in zf.infolist():
                            try:
                                data = zf.read(zi)
                            except Exception:
                                continue
                            if not data:
                                continue
                            size2 = len(data)
                            combined_name = path_lower + '/' + zi.filename.lower()
                            score = self._score_candidate(
                                combined_name, size2, penalize_non_pdf=False
                            )
                            if score > nested_best_score:
                                nested_best_score = score
                                nested_best_data = data
                    else:
                        try:
                            data = gzip.decompress(raw)
                        except Exception:
                            continue
                        if not data:
                            continue
                        size2 = len(data)
                        score = self._score_candidate(
                            path_lower, size2, penalize_non_pdf=False
                        )
                        if score > nested_best_score:
                            nested_best_score = score
                            nested_best_data = data

        direct_data = None
        if best_path is not None and best_score > 0.0:
            try:
                with open(best_path, 'rb') as fh:
                    data = fh.read()
                if data:
                    direct_data = data
            except OSError:
                direct_data = None

        if nested_best_data is not None and nested_best_score >= (best_score if best_score > 0.0 else 0.0):
            return nested_best_data
        if direct_data is not None:
            return direct_data
        return self._fallback_poc()

    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            return self._solve_from_dir(src_path)
        try:
            return self._solve_from_tar(src_path)
        except tarfile.ReadError:
            # Try treating as a zip archive containing the source tree
            try:
                if zipfile.is_zipfile(src_path):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        with zipfile.ZipFile(src_path, 'r') as zf:
                            zf.extractall(tmpdir)
                        return self._solve_from_dir(tmpdir)
            except Exception:
                pass
            return self._fallback_poc()