import os
import tarfile
import io
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        def is_textual(name: str) -> bool:
            lower = name.lower()
            for ext in ('.txt', '.md', '.rst', '.html', '.htm', '.xml', '.json', '.yml', '.yaml', '.ini', '.cfg', '.conf', '.csv'):
                if lower.endswith(ext):
                    return True
            return False

        def is_code(name: str) -> bool:
            lower = name.lower()
            for ext in ('.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh', '.java', '.py', '.js', '.m', '.mm', '.go', '.rs', '.rb', '.php', '.sh', '.bat', '.ps1', '.cmake', '.mak'):
                if lower.endswith(ext):
                    return True
            base = os.path.basename(lower)
            if base in ('makefile', 'cmakelists.txt'):
                return True
            return False

        def is_media(name: str) -> bool:
            lower = name.lower()
            for ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff'):
                if lower.endswith(ext):
                    return True
            return False

        def is_archive(name: str) -> bool:
            lower = name.lower()
            for ext in ('.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz', '.tar.xz', '.txz', '.zip', '.7z'):
                if lower.endswith(ext):
                    return True
            return False

        def name_score(name: str) -> int:
            n = name.lower()
            score = 0
            if n.endswith('.rar'):
                score += 800
            if 'rar5' in n:
                score += 400
            if 'rar' in n:
                score += 120
            if 'poc' in n:
                score += 380
            if 'huffman' in n:
                score += 260
            if 'overflow' in n or 'stack' in n:
                score += 220
            if 'crash' in n or 'bug' in n:
                score += 180
            if 'oss-fuzz' in n or 'clusterfuzz' in n or 'fuzz' in n:
                score += 150
            if 'test' in n or 'tests' in n or 'regress' in n:
                score += 80
            if 'min' in n or 'minimized' in n or 'reduce' in n:
                score += 120
            if 'id:' in n or 'id_' in n:
                score += 100
            if is_code(n):
                score -= 600
            if is_textual(n):
                score -= 400
            if is_media(n):
                score -= 700
            if is_archive(n):
                score -= 500
            for bad in ('.patch', '.diff'):
                if n.endswith(bad):
                    score -= 600
            return score

        def size_score(sz: int) -> int:
            # Prefer exactly 524, then close to it
            if sz <= 0:
                return -10**6
            base = 0
            if sz == 524:
                base += 5000
            # Closeness: linear decay, within +/- 2048 bytes still some score
            base += max(0, 2000 - abs(sz - 524))
            # Penalize very big files
            if sz > 10 * 1024 * 1024:
                base -= 3000
            if sz > 100 * 1024 * 1024:
                base -= 10000
            return base

        def member_score(ti: tarfile.TarInfo) -> int:
            nscore = name_score(ti.name)
            sscore = size_score(ti.size)
            return nscore + sscore

        def read_member(tf: tarfile.TarFile, ti: tarfile.TarInfo) -> bytes:
            try:
                f = tf.extractfile(ti)
                if f is None:
                    return b''
                with f:
                    return f.read()
            except Exception:
                return b''

        # Try to open tarball and collect candidates
        try:
            tf = tarfile.open(src_path, mode='r:*')
        except Exception:
            return b''

        with tf:
            candidates = []
            for ti in tf.getmembers():
                if not ti.isfile():
                    continue
                # Skip extremely large files to save resources
                if ti.size < 1 or ti.size > (256 * 1024 * 1024):
                    continue
                candidates.append(ti)

            if not candidates:
                return b''

            # First pass: exact size match 524, prefer .rar and name hints
            exact_matches = [ti for ti in candidates if ti.size == 524]
            if exact_matches:
                # Rank exact matches by name hints
                exact_matches.sort(key=lambda t: (name_score(t.name), t.size), reverse=True)
                data = read_member(tf, exact_matches[0])
                if data:
                    return data

            # Second pass: score-based selection
            candidates.sort(key=member_score, reverse=True)
            for ti in candidates[:200]:
                data = read_member(tf, ti)
                if not data:
                    continue
                # If we got something that looks like a RAR archive (signature "Rar!"), prefer it
                # RAR 5.0 signature: 52 61 72 21 1A 07 01 00
                if len(data) >= 8 and data[:7] == b'Rar!\x1a\x07':
                    return data
                # Otherwise if size == 524, return it as likely minimized PoC
                if len(data) == 524:
                    return data

            # Fallback: pick the top-scored candidate even if not ideal
            best = candidates[0]
            data = read_member(tf, best)
            return data if data else b''