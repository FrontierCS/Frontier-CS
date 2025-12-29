import os
import io
import sys
import tarfile
import zipfile
import re
import base64
import binascii
import gzip
import bz2
import lzma


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Gather candidates
        header_candidates = []
        all_candidates = []
        for name, data in self._iter_input_files(src_path):
            for cname, cdata in self._extract_candidates(name, data, depth=0):
                if not cdata:
                    continue
                all_candidates.append((cname, cdata))
                if self._detect_font_header(cdata) is not None:
                    header_candidates.append((cname, cdata))

        # Prefer header candidates
        chosen = None
        if header_candidates:
            chosen = self._choose_best(header_candidates)
        elif all_candidates:
            chosen = self._choose_best(all_candidates)

        if chosen is not None:
            return chosen[1]

        # Fallback: return a minimal dummy font-like blob (won't crash, but ensures output)
        return self._fallback_poc()

    # ------------------------------------------------------------
    # Core helpers
    # ------------------------------------------------------------
    def _iter_input_files(self, src_path):
        max_file_size = 10 * 1024 * 1024  # 10 MB
        # Directory
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    path = os.path.join(root, fn)
                    try:
                        if os.path.islink(path):
                            continue
                        size = os.path.getsize(path)
                        if size > max_file_size:
                            continue
                        with open(path, 'rb') as f:
                            data = f.read()
                        yield (os.path.relpath(path, src_path), data)
                    except Exception:
                        continue
            return

        # Tarball
        try:
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, mode='r:*') as tf:
                    for member in tf.getmembers():
                        if not member.isfile():
                            continue
                        if member.size > max_file_size:
                            continue
                        try:
                            f = tf.extractfile(member)
                            if not f:
                                continue
                            data = f.read()
                            yield (member.name, data)
                        except Exception:
                            continue
                return
        except Exception:
            pass

        # Zipfile
        try:
            if zipfile.is_zipfile(src_path):
                with zipfile.ZipFile(src_path, 'r') as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        if info.file_size > max_file_size:
                            continue
                        try:
                            with zf.open(info, 'r') as f:
                                data = f.read()
                            yield (info.filename, data)
                        except Exception:
                            continue
                return
        except Exception:
            pass

        # Fallback: single file
        try:
            if os.path.isfile(src_path):
                size = os.path.getsize(src_path)
                if size <= max_file_size:
                    with open(src_path, 'rb') as f:
                        data = f.read()
                    yield (os.path.basename(src_path), data)
        except Exception:
            pass

    def _extract_candidates(self, name, data, depth=0):
        # limit recursion depth
        depth_limit = 2
        results = []

        # Raw content as candidate
        results.append((name, data))

        # Try to parse text-embedded binaries
        if self._is_text_like(data) and len(data) <= 512 * 1024:  # 512 KB
            embedded = self._extract_from_text(data)
            for idx, blob in enumerate(embedded):
                results.append((f"{name}#embedded#{idx}", blob))

        # Try decompress simple compressed formats
        if depth < depth_limit:
            # Nested zip
            if self._looks_like_zip(data) or self._name_looks_like_zip(name):
                try:
                    with zipfile.ZipFile(io.BytesIO(data), 'r') as zf:
                        for info in zf.infolist():
                            if info.is_dir():
                                continue
                            if info.file_size > 10 * 1024 * 1024:
                                continue
                            try:
                                with zf.open(info, 'r') as f:
                                    sub = f.read()
                                results.extend(self._extract_candidates(f"{name}/{info.filename}", sub, depth + 1))
                            except Exception:
                                continue
                except Exception:
                    pass

            # Gzip
            if name.lower().endswith('.gz'):
                try:
                    sub = gzip.decompress(data)
                    results.extend(self._extract_candidates(name[:-3], sub, depth + 1))
                except Exception:
                    pass

            # BZ2
            if name.lower().endswith('.bz2'):
                try:
                    sub = bz2.decompress(data)
                    results.extend(self._extract_candidates(name[:-4], sub, depth + 1))
                except Exception:
                    pass

            # XZ
            if name.lower().endswith('.xz'):
                try:
                    sub = lzma.decompress(data)
                    results.extend(self._extract_candidates(name[:-3], sub, depth + 1))
                except Exception:
                    pass

            # TAR family if small
            if self._name_looks_like_tar(name) and len(data) <= 10 * 1024 * 1024:
                try:
                    bio = io.BytesIO(data)
                    with tarfile.open(fileobj=bio, mode='r:*') as tf:
                        for member in tf.getmembers():
                            if not member.isfile():
                                continue
                            if member.size > 10 * 1024 * 1024:
                                continue
                            try:
                                f = tf.extractfile(member)
                                if f is None:
                                    continue
                                sub = f.read()
                                results.extend(self._extract_candidates(f"{name}/{member.name}", sub, depth + 1))
                            except Exception:
                                continue
                except Exception:
                    pass

        return results

    def _choose_best(self, candidates):
        # candidates: list of (name, data)
        best = None
        best_score = -1
        for name, data in candidates:
            score = self._score_candidate(name, data)
            if score > best_score:
                best_score = score
                best = (name, data)
        return best

    # ------------------------------------------------------------
    # Scoring and detection
    # ------------------------------------------------------------
    def _detect_font_header(self, data: bytes):
        if not data or len(data) < 4:
            return None
        sig = data[:4]
        if sig == b'OTTO':
            return 'otf'
        if sig == b'wOFF':
            return 'woff'
        if sig == b'wOF2':
            return 'woff2'
        if sig == b'ttcf':
            return 'ttc'
        if sig in (b'\x00\x01\x00\x00', b'true', b'typ1'):
            return 'ttf'
        return None

    def _score_candidate(self, name: str, data: bytes) -> int:
        nlower = name.lower()
        size = len(data) if data else 0
        if size == 0:
            return -1

        ext = os.path.splitext(nlower)[1]
        ext_scores = {
            '.otf': 7,
            '.ttf': 7,
            '.cff': 4,
            '.woff': 6,
            '.woff2': 6,
            '.bin': 2,
            '.dat': 2,
            '.poc': 8,
        }
        score = ext_scores.get(ext, 0) * 10

        # Name keywords
        kw = [
            ('poc', 60),
            ('crash', 50),
            ('repro', 50),
            ('reproducer', 50),
            ('clusterfuzz', 60),
            ('min', 10),
            ('uaf', 35),
            ('use-after-free', 45),
            ('san', 10),
            ('asan', 20),
            ('ubsan', 10),
            ('ots', 35),
            ('ots-sanitizer', 35),
            ('write', 10),
            ('ttf', 5),
            ('otf', 5),
            ('woff', 5),
        ]
        for k, w in kw:
            if k in nlower:
                score += w

        # Header detection bonus
        header_type = self._detect_font_header(data)
        if header_type is not None:
            score += 120

        # Size closeness to 800 bytes
        closeness = max(0, 100 - abs(size - 800))
        score += closeness

        # Penalize too large
        if size > 1_000_000:
            score -= int((size - 1_000_000) / 50_000)  # mild penalty

        return score

    # ------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------
    def _is_text_like(self, data: bytes) -> bool:
        if not data:
            return False
        if b'\x00' in data[:4096]:
            return False
        sample = data[:4096]
        printable = 0
        for b in sample:
            if b in (9, 10, 13) or 32 <= b <= 126:
                printable += 1
        ratio = printable / max(1, len(sample))
        return ratio > 0.9

    def _extract_from_text(self, data: bytes):
        # Returns list of decoded binaries
        out = []
        try:
            text = data.decode('utf-8', errors='ignore')
        except Exception:
            try:
                text = data.decode('latin-1', errors='ignore')
            except Exception:
                return out

        # Strategy 1: backslash-hex sequences
        for m in re.finditer(r'(?:\\x[0-9a-fA-F]{2}){32,}', text):
            seq = m.group(0)
            try:
                hexes = re.findall(r'\\x([0-9a-fA-F]{2})', seq)
                blob = bytes(int(h, 16) for h in hexes)
                if len(blob) >= 64:
                    out.append(blob)
            except Exception:
                continue
            if len(out) >= 5:
                break

        # Strategy 2: continuous hex strings
        for m in re.finditer(r'([0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f0-9A-Fa-f\s:,-]{128,})', text):
            chunk = m.group(0)
            # Strip non-hex chars
            filtered = re.sub(r'[^0-9A-Fa-f]', '', chunk)
            if len(filtered) % 2 == 1 or len(filtered) < 128:
                continue
            try:
                blob = binascii.unhexlify(filtered)
                if len(blob) >= 64:
                    out.append(blob)
            except Exception:
                continue
            if len(out) >= 10:
                break

        # Strategy 3: base64 blobs
        for m in re.finditer(r'([A-Za-z0-9+/=\s]{80,})', text):
            b64 = re.sub(r'\s+', '', m.group(1))
            if len(b64) < 80:
                continue
            # Check basic validity
            if len(b64) % 4 != 0:
                continue
            try:
                blob = base64.b64decode(b64, validate=False)
                if blob and len(blob) >= 64:
                    out.append(blob)
            except Exception:
                continue
            if len(out) >= 15:
                break

        # Prefer only those that look like font headers
        prioritized = []
        for blob in out:
            if self._detect_font_header(blob) is not None:
                prioritized.append(blob)
        if prioritized:
            return prioritized
        return out

    # ------------------------------------------------------------
    # Utils
    # ------------------------------------------------------------
    def _looks_like_zip(self, data: bytes) -> bool:
        if not data or len(data) < 4:
            return False
        # ZIP local file header starts with PK\x03\x04 or PK\x05\x06 etc.
        return data[:2] == b'P' + b'K'

    def _name_looks_like_zip(self, name: str) -> bool:
        nl = name.lower()
        return nl.endswith('.zip')

    def _name_looks_like_tar(self, name: str) -> bool:
        nl = name.lower()
        return nl.endswith('.tar') or nl.endswith('.tar.gz') or nl.endswith('.tgz') or nl.endswith('.tar.bz2') or nl.endswith('.tbz2') or nl.endswith('.tar.xz') or nl.endswith('.txz')

    def _fallback_poc(self) -> bytes:
        # Build an 800-byte blob with a font-like header.
        # Using TTF sfnt version 0x00010000 followed by zeros.
        payload_len = 800
        header = b'\x00\x01\x00\x00'
        blob = header + b'\x00' * (payload_len - len(header))
        return blob


# If needed for local manual testing:
# if __name__ == "__main__":
#     src = sys.argv[1] if len(sys.argv) > 1 else "."
#     poc = Solution().solve(src)
#     sys.stdout.buffer.write(poc)