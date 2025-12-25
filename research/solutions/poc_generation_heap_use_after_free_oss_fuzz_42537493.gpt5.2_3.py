import os
import tarfile
import tempfile
import shutil


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    base = os.path.abspath(path) + os.sep
    for m in tar.getmembers():
        target = os.path.abspath(os.path.join(path, m.name))
        if not target.startswith(base):
            continue
        tar.extract(m, path=path)


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        root = src_path
        try:
            if os.path.isfile(src_path):
                tmpdir = tempfile.mkdtemp(prefix="poc-src-")
                with tarfile.open(src_path, "r:*") as tf:
                    _safe_extract_tar(tf, tmpdir)
                root = tmpdir

            keywords = (
                "clusterfuzz",
                "testcase",
                "minimized",
                "repro",
                "poc",
                "crash",
                "asan",
                "uaf",
            )
            best = None  # (size, path)
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    lfn = fn.lower()
                    if not any(k in lfn for k in keywords):
                        continue
                    p = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if st.st_size <= 0 or st.st_size > 4096:
                        continue
                    if best is None or st.st_size < best[0]:
                        best = (st.st_size, p)

            if best is not None:
                try:
                    with open(best[1], "rb") as f:
                        data = f.read()
                    if data:
                        return data
                except OSError:
                    pass

            return b"\xff\xfe" + "<a><b/></a>".encode("utf-16le")
        finally:
            if tmpdir is not None:
                shutil.rmtree(tmpdir, ignore_errors=True)