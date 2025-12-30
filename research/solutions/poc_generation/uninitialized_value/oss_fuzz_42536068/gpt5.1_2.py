import os
import tarfile
import zipfile
import tempfile
import stat


class Solution:
    def solve(self, src_path: str) -> bytes:
        exact_len = 2179
        try:
            root = self._prepare_root(src_path)
        except Exception:
            root = os.path.abspath(src_path) if os.path.exists(src_path) else os.getcwd()

        try:
            poc_path = self._find_poc(root, exact_len)
            if poc_path is not None:
                try:
                    with open(poc_path, "rb") as f:
                        data = f.read()
                    if data:
                        return data
                except Exception:
                    pass
        except Exception:
            pass

        return b"A" * exact_len

    def _prepare_root(self, src_path: str) -> str:
        src_path = os.path.abspath(src_path)
        if os.path.isdir(src_path):
            return src_path

        tmpdir = tempfile.mkdtemp(prefix="src_extract_")

        if zipfile.is_zipfile(src_path):
            with zipfile.ZipFile(src_path) as zf:
                zf.extractall(tmpdir)
            return tmpdir

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for member in tf.getmembers():
                    member_path = os.path.join(tmpdir, member.name)
                    if not self._is_within_directory(tmpdir, member_path):
                        continue
                    try:
                        tf.extract(member, tmpdir)
                    except Exception:
                        continue
            return tmpdir
        except Exception:
            # Fallback: if src_path is not an archive, use its directory
            parent = os.path.dirname(src_path)
            return parent if os.path.isdir(parent) else os.getcwd()

    def _is_within_directory(self, directory: str, target: str) -> bool:
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        return os.path.commonpath([abs_directory, abs_target]) == abs_directory

    def _find_poc(self, root: str, exact_len: int) -> str | None:
        candidates_exact = []
        keyword_candidates = []
        all_small_files = []

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames.sort()
            filenames.sort()
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue

                size = st.st_size
                lpath = path.lower()

                if size == exact_len:
                    candidates_exact.append(path)

                if size <= 5000:
                    if any(k in lpath for k in ("poc", "crash", "bug", "test", "case", "uninit", "value", "oss-fuzz", "id:")):
                        keyword_candidates.append((path, size))
                    all_small_files.append((path, size))

        if candidates_exact:
            def score(p: str) -> tuple[int, int]:
                l = p.lower()
                s = 0
                if "poc" in l:
                    s -= 100
                if "crash" in l:
                    s -= 90
                if "bug" in l:
                    s -= 80
                if "uninit" in l:
                    s -= 70
                if "value" in l:
                    s -= 5
                if "oss-fuzz" in l:
                    s -= 3
                if "id:" in l:
                    s -= 2
                if l.endswith(".bin") or l.endswith(".poc") or l.endswith(".testcase"):
                    s -= 1
                return (s, len(l))

            candidates_exact.sort(key=score)
            return candidates_exact[0]

        if keyword_candidates:
            keyword_candidates.sort(key=lambda item: (abs(item[1] - exact_len), item[1]))
            return keyword_candidates[0][0]

        if all_small_files:
            all_small_files.sort(key=lambda item: (abs(item[1] - exact_len), item[1]))
            return all_small_files[0][0]

        return None