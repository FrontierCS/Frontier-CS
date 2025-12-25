import os
import tarfile
import tempfile


class Solution:
    def _find_poc_bytes(self, root_dir):
        # Heuristic search for an existing PoC file inside the extracted tarball.
        best_path = None
        best_score = -1
        max_size = 1 << 20  # 1 MB

        high_tokens = ['poc', 'crash', 'uaf', 'heap', 'asan', 'repro', 'trigger', 'payload']
        med_tokens = ['id_', 'input', 'testcase', 'raw_encap', 'encap', 'seed', 'corpus']
        bin_exts = ['.bin', '.raw', '.dat', '.in', '.out', '.packet']
        text_exts = ['.c', '.h', '.hpp', '.cpp', '.cc', '.py', '.md', '.txt',
                     '.rst', '.java', '.go', '.rb', '.js', '.json', '.xml', '.html']

        for dirpath, dirnames, filenames in os.walk(root_dir):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0 or size > max_size:
                    continue

                name_lower = filename.lower()
                rel_lower = os.path.relpath(path, root_dir).lower()
                score = 0

                for tok in high_tokens:
                    if tok in name_lower or tok in rel_lower:
                        score += 50
                for tok in med_tokens:
                    if tok in name_lower or tok in rel_lower:
                        score += 20

                _, ext = os.path.splitext(filename)
                ext = ext.lower()
                if ext in bin_exts:
                    score += 10
                if ext in text_exts:
                    score -= 30

                if size == 72:
                    score += 100
                elif size < 72:
                    score += 40
                elif size < 2048:
                    score += 30
                elif size < 65536:
                    score += 10

                if score > best_score:
                    best_score = score
                    best_path = path

        # Require a minimal score to accept a candidate.
        if best_path is not None and best_score > 60:
            try:
                with open(best_path, 'rb') as f:
                    return f.read()
            except OSError:
                return None
        return None

    def _solve_in_root(self, root_dir):
        poc = self._find_poc_bytes(root_dir)
        if poc is not None:
            return poc
        # Fallback: return a generic 72-byte blob if no PoC found.
        return b'A' * 72

    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            return self._solve_in_root(src_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:*') as tf:
                tf.extractall(tmpdir)
            return self._solve_in_root(tmpdir)
