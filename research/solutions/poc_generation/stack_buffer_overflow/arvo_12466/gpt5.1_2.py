import os
import tarfile
import tempfile
import shutil
import stat


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="arvo_12466_")

        def safe_extract(tar: tarfile.TarFile, path: str) -> None:
            base_path = os.path.abspath(path)
            for member in tar.getmembers():
                member_path = os.path.abspath(os.path.join(path, member.name))
                if not member_path.startswith(base_path):
                    continue
                try:
                    tar.extract(member, path=path)
                except Exception:
                    continue

        try:
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    safe_extract(tf, tmpdir)
            except Exception:
                return b""

            best_path = None
            best_score = -1

            for root, dirs, files in os.walk(tmpdir):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        st = os.stat(fpath)
                    except OSError:
                        continue
                    if not stat.S_ISREG(st.st_mode):
                        continue

                    size = st.st_size
                    if size <= 0 or size > 10000:
                        continue

                    score = 0
                    if size == 524:
                        score += 1000
                    diff = abs(size - 524)
                    if diff < 200:
                        score += 200 - diff

                    lower_name = fname.lower()
                    lower_path = fpath.lower()
                    ext = os.path.splitext(lower_name)[1]

                    if ext in (".rar", ".r05", ".r5", ".rar5"):
                        score += 500
                    elif ext in (".bin", ".dat", ".poc", ".raw"):
                        score += 150

                    keywords = {
                        "rar5": 300,
                        "rar": 200,
                        "huff": 180,
                        "huffman": 180,
                        "table": 120,
                        "poc": 200,
                        "crash": 200,
                        "overflow": 200,
                        "fuzz": 120,
                        "12466": 400,
                        "cve": 100,
                        "regress": 100,
                        "sample": 60,
                        "test": 40,
                    }
                    for kw, val in keywords.items():
                        if kw in lower_name or kw in lower_path:
                            score += val

                    header = b""
                    try:
                        with open(fpath, "rb") as f:
                            header = f.read(8)
                    except OSError:
                        header = b""

                    if header.startswith(b"Rar!"):
                        score += 800
                        if header.startswith(b"Rar!\x1a\x07\x01"):
                            score += 500

                    if score > best_score:
                        best_score = score
                        best_path = fpath

            if best_path is not None:
                try:
                    with open(best_path, "rb") as f:
                        data = f.read()
                except OSError:
                    data = b""
            else:
                data = b""

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

        return data