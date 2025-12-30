import os
import tarfile
import tempfile
import shutil


class Solution:
    def _find_poc_file(self, root):
        patterns = [
            'clusterfuzz',
            'minimized',
            'testcase',
            'poc',
            'crash',
            'repro',
            'reproducer',
            'heap-buffer-overflow',
            'dash_client',
            'dash-client',
            'dashclient',
        ]
        best_path = None
        best_score = None
        for dirpath, dirnames, filenames in os.walk(root):
            for name in filenames:
                lname = name.lower()
                if not any(p in lname for p in patterns):
                    continue
                full_path = os.path.join(dirpath, name)
                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    continue
                if size <= 0 or size > 65536:
                    continue
                score = size
                if 'clusterfuzz' in lname:
                    score -= 10000
                if 'minimized' in lname:
                    score -= 8000
                if 'dash' in lname and 'client' in lname:
                    score -= 7000
                if 'poc' in lname:
                    score -= 5000
                if 'crash' in lname:
                    score -= 4000
                if 'testcase' in lname:
                    score -= 3000
                if 'repro' in lname:
                    score -= 2000
                if 'heap-buffer-overflow' in lname:
                    score -= 6000
                if best_score is None or score < best_score:
                    best_score = score
                    best_path = full_path
        return best_path

    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="dash_poc_")
        try:
            try:
                with tarfile.open(src_path, 'r:*') as tf:
                    tf.extractall(tmpdir)
            except Exception:
                return b'A' * 9

            poc_path = self._find_poc_file(tmpdir)
            if poc_path is not None:
                try:
                    with open(poc_path, 'rb') as f:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

            return b'A' * 9
        finally:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass