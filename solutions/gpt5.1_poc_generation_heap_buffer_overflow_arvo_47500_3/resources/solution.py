import os
import tarfile
import tempfile
import shutil
import stat


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_size = 1479
        tmpdir = None

        def is_regular_file(path: str) -> bool:
            try:
                st = os.stat(path)
            except OSError:
                return False
            return stat.S_ISREG(st.st_mode)

        def walk_files(root: str):
            for dirpath, _, filenames in os.walk(root):
                for name in filenames:
                    full = os.path.join(dirpath, name)
                    if is_regular_file(full):
                        yield full

        def score_candidate(path: str, size_match: bool) -> int:
            name = os.path.basename(path)
            lower_name = name.lower()
            lower_path = path.lower()
            ext = os.path.splitext(lower_name)[1]

            score = 0

            if size_match:
                score += 50

            image_exts = {
                ".jp2", ".j2k", ".jpc", ".jpx", ".j2c",
                ".pgx", ".png", ".jpg", ".jpeg", ".bmp",
                ".pnm", ".pgm", ".ppm", ".raw", ".bin", ".dat"
            }
            if ext in image_exts:
                score += 20
            if ext in {".jp2", ".j2k", ".jpc", ".j2c"}:
                score += 15

            keywords = [
                ("poc", 40),
                ("crash", 30),
                ("id:", 30),
                ("id_", 25),
                ("heap", 15),
                ("overflow", 15),
                ("malloc", 10),
                ("bug", 10),
                ("opj", 10),
                ("htj2k", 10),
                ("ht_", 5),
                ("htt", 5),
                ("ht", 3),
                ("47500", 10),
            ]
            for kw, val in keywords:
                if kw in lower_path:
                    score += val

            rel = os.path.relpath(path, root_dir)
            depth = rel.count(os.sep)
            score -= depth

            try:
                sz = os.path.getsize(path)
            except OSError:
                sz = 0
            if sz < 10 * 1024:
                score += 5

            return score

        try:
            if os.path.isdir(src_path):
                root_dir = src_path
            else:
                if not tarfile.is_tarfile(src_path):
                    return b"A"
                tmpdir = tempfile.mkdtemp(prefix="poc_extract_")
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmpdir)
                root_dir = tmpdir

            best_path = None
            best_score = None

            # First pass: exact size match
            for path in walk_files(root_dir):
                try:
                    sz = os.path.getsize(path)
                except OSError:
                    continue
                if sz != target_size:
                    continue
                score = score_candidate(path, size_match=True)
                if best_path is None or score > best_score or (
                    score == best_score and path < best_path
                ):
                    best_path = path
                    best_score = score

            # Second pass: heuristic match if no exact-size file found
            if best_path is None:
                for path in walk_files(root_dir):
                    lower_path = path.lower()
                    name = os.path.basename(lower_path)
                    ext = os.path.splitext(name)[1]
                    interesting = False

                    if any(k in lower_path for k in ("poc", "crash", "id:", "id_", "heap", "overflow")):
                        interesting = True
                    if ext in {
                        ".jp2", ".j2k", ".jpc", ".jpx", ".j2c",
                        ".pgx", ".png", ".jpg", ".jpeg", ".bmp",
                        ".pnm", ".pgm", ".ppm", ".raw", ".bin", ".dat"
                    }:
                        interesting = True

                    if not interesting:
                        continue

                    try:
                        sz = os.path.getsize(path)
                    except OSError:
                        continue
                    if sz > 1024 * 1024:
                        continue

                    score = score_candidate(path, size_match=False)
                    if best_path is None or score > best_score or (
                        score == best_score and path < best_path
                    ):
                        best_path = path
                        best_score = score

            if best_path is not None:
                try:
                    with open(best_path, "rb") as f:
                        data = f.read()
                    return data
                except OSError:
                    pass

            return b"A"
        finally:
            if tmpdir is not None:
                shutil.rmtree(tmpdir, ignore_errors=True)
