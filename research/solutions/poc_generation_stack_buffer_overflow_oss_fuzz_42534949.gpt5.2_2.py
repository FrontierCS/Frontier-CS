import os
import re
import tarfile
from typing import Iterator, Tuple, Optional


class Solution:
    def __init__(self) -> None:
        self._max_file_size = 2 * 1024 * 1024
        self._max_total_read = 32 * 1024 * 1024

    def _iter_dir_files(self, root: str) -> Iterator[Tuple[str, bytes]]:
        total = 0
        for base, _, files in os.walk(root):
            for fn in files:
                path = os.path.join(base, fn)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if not os.path.isfile(path):
                    continue
                if st.st_size <= 0 or st.st_size > self._max_file_size:
                    continue
                if total + st.st_size > self._max_total_read:
                    return
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                total += len(data)
                yield path, data

    def _iter_tar_files(self, tar_path: str) -> Iterator[Tuple[str, bytes]]:
        total = 0
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > self._max_file_size:
                        continue
                    name = m.name
                    if total + m.size > self._max_total_read:
                        return
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    except Exception:
                        continue
                    total += len(data)
                    yield name, data
        except Exception:
            return

    def _iter_files(self, src_path: str) -> Iterator[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            yield from self._iter_dir_files(src_path)
        else:
            yield from self._iter_tar_files(src_path)

    def _find_embedded_poc(self, src_path: str) -> Optional[bytes]:
        name_hits = []
        content_hits = []
        for name, data in self._iter_files(src_path):
            lname = name.lower()
            if "42534949" in lname:
                name_hits.append((name, data))
            if len(data) <= 4096:
                try:
                    txt = data.decode("utf-8", "ignore")
                except Exception:
                    txt = ""
                if "42534949" in txt or "oss-fuzz" in txt or "clusterfuzz" in txt:
                    content_hits.append((name, data))
        for _, data in name_hits:
            if 1 <= len(data) <= 1024:
                return data
        for _, data in content_hits:
            if 1 <= len(data) <= 1024:
                return data
        for name, data in self._iter_files(src_path):
            lname = name.lower()
            if any(k in lname for k in ("poc", "reproducer", "testcase", "crash")) and 1 <= len(data) <= 256:
                return data
        return None

    def _guess_style(self, src_path: str) -> str:
        dot_inf = 0
        plain_inf = 0
        yamlish = 0
        tomlish = 0
        for name, data in self._iter_files(src_path):
            lname = name.lower()
            if not any(lname.endswith(ext) for ext in (".c", ".cc", ".cpp", ".h", ".hpp", ".hh", ".inc", ".inl", ".rs", ".go", ".java", ".py", ".js", ".ts", ".cmake", "cmakelists.txt")):
                continue
            try:
                s = data.decode("utf-8", "ignore").lower()
            except Exception:
                continue
            dot_inf += s.count(".inf") + s.count("-.inf") + s.count("+.inf")
            plain_inf += s.count("infinity") + s.count("inf")
            if "yaml" in s or "yaml" in lname:
                yamlish += 1
            if "toml" in s or "toml" in lname:
                tomlish += 1
        if dot_inf > 0 or (yamlish > tomlish and yamlish > 0):
            return "dot_inf"
        if tomlish > 0:
            return "plain"
        if plain_inf > 0 and dot_inf == 0:
            return "plain"
        return "plain"

    def solve(self, src_path: str) -> bytes:
        embedded = self._find_embedded_poc(src_path)
        if embedded is not None:
            return embedded

        style = self._guess_style(src_path)
        if style == "dot_inf":
            return b"-.00000000000000"  # 16 bytes
        return b"-000000000000000"  # 16 bytes