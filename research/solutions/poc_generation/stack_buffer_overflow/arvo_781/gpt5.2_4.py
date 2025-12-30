import os
import re
import struct
import tarfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        best_name, best_code = self._load_best_harness(src_path)
        if not best_code:
            return b"\x00" * 8

        min_size = self._infer_min_size(best_code)
        if min_size <= 0:
            min_size = 8
        if min_size < 8:
            min_size = 8

        # Prefer explicit fixed-size header parsing (often tied to 8-byte PoCs)
        reads = self._find_fixed_reads(best_code)
        if reads:
            return self._gen_from_fixed_reads(best_code, reads, min_size)

        # Next: FuzzedDataProvider-based harness
        if "FuzzedDataProvider" in best_code:
            b = self._gen_from_fdp(best_code, min_size)
            if b is not None:
                return b

        # Next: delimiter split harness
        b = self._gen_from_delim(best_code, min_size)
        if b is not None:
            return b

        # Next: half-split harness
        if re.search(r"\bsize\s*/\s*2\b", best_code) or re.search(r"\bSize\s*/\s*2\b", best_code):
            s = (b".*" * 4)[:min_size]
            if len(s) < min_size:
                s += b"." * (min_size - len(s))
            return s

        # Fallback: 8 bytes header-ish that often compiles as empty pattern/subject
        return b"\x00" * min_size

    def _read_text_from_bytes(self, data: bytes) -> str:
        try:
            return data.decode("utf-8", "ignore")
        except Exception:
            try:
                return data.decode("latin-1", "ignore")
            except Exception:
                return ""

    def _iter_source_files_from_dir(self, root: str):
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".inc")
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                lf = fn.lower()
                if lf.endswith(exts) or "fuzz" in lf or "fuzzer" in lf:
                    p = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(p)
                        if st.st_size > 2_000_000:
                            continue
                        with open(p, "rb") as f:
                            yield p, f.read()
                    except Exception:
                        continue

    def _iter_source_files_from_tar(self, tar_path: str):
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".inc")
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    name = m.name
                    lname = name.lower()
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    if lname.endswith(exts) or "fuzz" in lname or "fuzzer" in lname:
                        try:
                            f = tf.extractfile(m)
                            if not f:
                                continue
                            yield name, f.read()
                        except Exception:
                            continue
        except Exception:
            return

    def _score_harness(self, name: str, code: str) -> int:
        lname = name.lower()
        s = 0
        if "llvmfuzzertestoneinput" in code:
            s += 80
        if "afl_fuzz_init" in code or "afl" in code and "fuzz" in code:
            s += 30
        if "fuzzeddataprovider" in code:
            s += 20
        if "fuzz" in lname or "fuzzer" in lname:
            s += 15
        if "pcre" in code or "pcre2" in code:
            s += 20
        if "ovector" in code or "ovecsize" in code or "ovec" in code:
            s += 15
        if "dfa_match" in code or "dfa_exec" in code:
            s += 25
        if "pcre2_dfa_match" in code or "pcre_dfa_exec" in code:
            s += 30
        if "pcre2_compile" in code or "pcre_compile" in code:
            s += 10
        if "pcre2_match" in code or "pcre_exec" in code:
            s += 10
        if "stdin" in code and ("fread" in code or "read(" in code):
            s += 8
        return s

    def _load_best_harness(self, src_path: str) -> Tuple[str, str]:
        best = ("", "")
        best_score = -1

        if os.path.isdir(src_path):
            it = self._iter_source_files_from_dir(src_path)
        else:
            it = self._iter_source_files_from_tar(src_path)

        for name, b in it:
            code = self._read_text_from_bytes(b)
            if not code:
                continue
            sc = self._score_harness(name, code)
            if sc > best_score:
                best_score = sc
                best = (name, code)

        return best

    def _infer_min_size(self, code: str) -> int:
        mins = []
        for m in re.finditer(r"if\s*\(\s*(?:Size|size)\s*(<|<=)\s*(\d+)\s*\)", code):
            op = m.group(1)
            n = int(m.group(2))
            if op == "<=":
                n += 1
            mins.append(n)
        # handle patterns like: if (size < 8u)
        for m in re.finditer(r"if\s*\(\s*(?:Size|size)\s*(<|<=)\s*(\d+)\s*[uUlL]?\s*\)", code):
            op = m.group(1)
            n = int(m.group(2))
            if op == "<=":
                n += 1
            mins.append(n)
        return max(mins) if mins else 0

    def _find_fixed_reads(self, code: str) -> List[Tuple[str, int, int]]:
        reads = []

        # memcpy(&var, data + off, N)
        for m in re.finditer(
            r"memcpy\s*\(\s*&\s*([A-Za-z_]\w*)\s*,\s*(?:Data|data)\s*\+\s*(\d+)\s*,\s*(\d+)\s*\)",
            code,
        ):
            var = m.group(1)
            off = int(m.group(2))
            n = int(m.group(3))
            if n in (1, 2, 4, 8):
                reads.append((var, off, n))

        # var = *(const uint32_t*)(data + off)
        for m in re.finditer(
            r"([A-Za-z_]\w*)\s*=\s*\*\s*\(\s*(?:const\s+)?(?:u?int(?:8|16|32|64)_t)\s*\*\s*\)\s*\(\s*(?:Data|data)\s*\+\s*(\d+)\s*\)",
            code,
        ):
            var = m.group(1)
            off = int(m.group(2))
            # Try to infer size from nearby cast text
            cast_snip = code[max(0, m.start() - 64):m.end() + 64]
            sz = 4
            if "int8_t" in cast_snip:
                sz = 1
            elif "int16_t" in cast_snip:
                sz = 2
            elif "int32_t" in cast_snip:
                sz = 4
            elif "int64_t" in cast_snip:
                sz = 8
            reads.append((var, off, sz))

        # Read32(data + off) / ReadU32(...)
        for m in re.finditer(
            r"([A-Za-z_]\w*)\s*=\s*Read(?:U)?(8|16|32|64)\s*\(\s*(?:Data|data)\s*\+\s*(\d+)\s*\)",
            code,
        ):
            var = m.group(1)
            bits = int(m.group(2))
            off = int(m.group(3))
            reads.append((var, off, bits // 8))

        # de-dup by (var,off,sz)
        seen = set()
        out = []
        for r in reads:
            if r in seen:
                continue
            seen.add(r)
            out.append(r)
        return out

    def _classify_var(self, code: str, var: str) -> str:
        v = var.lower()
        if "ovec" in v or "ovector" in v or "ovecsize" in v:
            return "ovector"
        if "opt" in v or "option" in v or "flag" in v:
            return "options"
        if "mode" in v or "dfa" in v or "engine" in v or "type" in v:
            return "mode"
        if "len" in v or "length" in v or "size" in v:
            # disambiguate: if used in pointer arithmetic / slicing, likely length
            if re.search(r"\b" + re.escape(var) + r"\b", code):
                # If it's passed to compile as options it's not length
                if re.search(r"compile\s*\([^;]*\b" + re.escape(var) + r"\b", code, re.IGNORECASE):
                    return "options"
                if re.search(r"\b" + re.escape(var) + r"\b\s*\+\s*(?:\d+|sizeof)", code):
                    return "len"
            return "len"
        return "unknown"

    def _pack_le(self, value: int, nbytes: int) -> bytes:
        if nbytes == 1:
            return struct.pack("<B", value & 0xFF)
        if nbytes == 2:
            return struct.pack("<H", value & 0xFFFF)
        if nbytes == 4:
            return struct.pack("<I", value & 0xFFFFFFFF)
        if nbytes == 8:
            return struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF)
        # generic
        return int(value).to_bytes(nbytes, "little", signed=False)

    def _gen_from_fixed_reads(self, code: str, reads: List[Tuple[str, int, int]], min_size: int) -> bytes:
        # If reads strongly suggest a header-only harness, generate a header PoC.
        # Keep as small as allowed: min_size.
        buf = bytearray(b"\x00" * min_size)

        # If there are reads beyond min_size, expand cautiously.
        max_end = max(off + sz for _, off, sz in reads)
        if max_end > len(buf):
            buf.extend(b"\x00" * (max_end - len(buf)))

        # Determine if any var is length-like (pattern_len/subject_len) -> keep 0.
        # Determine ovector size -> large enough to satisfy mismatch with 0 captures.
        # Determine options -> 0.
        # Determine mode -> 1.
        any_len = False
        any_ovec = False
        any_opts = False

        classified = []
        for var, off, sz in reads:
            cls = self._classify_var(code, var)
            classified.append((cls, var, off, sz))
            if cls == "len":
                any_len = True
            elif cls == "ovector":
                any_ovec = True
            elif cls == "options":
                any_opts = True

        for cls, var, off, sz in classified:
            if cls == "len":
                val = 0
            elif cls == "options":
                val = 0
            elif cls == "mode":
                val = 1
            elif cls == "ovector":
                val = 1024 if sz >= 2 else 16
            else:
                # If the header appears to be lengths (any_len), keep unknowns at 0
                # Otherwise, try to set an unknown second field to a reasonable ovecsize-ish value
                val = 0

            buf[off:off + sz] = self._pack_le(val, sz)

        # If we didn't identify any meaningful fields, apply a generic safe header:
        # offset 0: 0 (often options or length), offset 4: 1024 (often ovecsize)
        if not any_len and not any_ovec and not any_opts:
            if len(buf) < 8:
                buf.extend(b"\x00" * (8 - len(buf)))
            buf[0:4] = self._pack_le(0, 4)
            buf[4:8] = self._pack_le(1024, 4)

        return bytes(buf[:min_size])

    def _type_size(self, t: str) -> int:
        tt = t.strip()
        tt = re.sub(r"\bconst\b", "", tt)
        tt = re.sub(r"\s+", "", tt)
        tt_l = tt.lower()

        if "uint8_t" in tt_l or "int8_t" in tt_l or tt_l in ("char", "unsignedchar", "signedchar", "uint8", "int8"):
            return 1
        if "uint16_t" in tt_l or "int16_t" in tt_l or tt_l in ("short", "unsignedshort", "int16", "uint16"):
            return 2
        if "uint32_t" in tt_l or "int32_t" in tt_l or tt_l in ("int", "unsigned", "unsignedint", "uint32", "int32"):
            return 4
        if "uint64_t" in tt_l or "int64_t" in tt_l or "longlong" in tt_l or "unsignedlonglong" in tt_l:
            return 8
        if "size_t" in tt_l or "uintptr_t" in tt_l or "intptr_t" in tt_l:
            return struct.calcsize("P")
        if tt_l == "long" or tt_l == "unsignedlong":
            return struct.calcsize("l")
        return 4

    def _parse_int_token(self, tok: str) -> Optional[int]:
        tok = tok.strip()
        tok = tok.strip("()")
        tok = tok.split()[0]
        if not tok:
            return None
        if re.fullmatch(r"[-+]?0[xX][0-9a-fA-F]+", tok) or re.fullmatch(r"[-+]?\d+", tok):
            try:
                return int(tok, 0)
            except Exception:
                return None
        return None

    def _gen_from_fdp(self, code: str, min_size: int) -> Optional[bytes]:
        # Try to interpret first few consumes and choose values to force vulnerable path.
        # We'll build exactly min_size bytes.
        # If consumes exceed min_size, fall back to generic.
        fn_pos = code.find("LLVMFuzzerTestOneInput")
        if fn_pos == -1:
            fn_pos = 0
        snippet = code[fn_pos:fn_pos + 20000]

        consumes = []
        # auto var = provider.ConsumeIntegralInRange<type>(min,max);
        for m in re.finditer(
            r"(?:auto|const\s+auto|unsigned|int|uint(?:8|16|32|64)_t|size_t)\s+([A-Za-z_]\w*)\s*=\s*provider\.ConsumeIntegralInRange<\s*([^>]+)\s*>\(\s*([^,]+)\s*,\s*([^)]+)\s*\)\s*;",
            snippet,
        ):
            var = m.group(1)
            typ = m.group(2)
            mn = self._parse_int_token(m.group(3))
            mx = self._parse_int_token(m.group(4))
            consumes.append(("inrange", var, typ, mn, mx, m.start()))

        # var = provider.ConsumeIntegral<type>();
        for m in re.finditer(
            r"(?:auto|const\s+auto|unsigned|int|uint(?:8|16|32|64)_t|size_t)\s+([A-Za-z_]\w*)\s*=\s*provider\.ConsumeIntegral<\s*([^>]+)\s*>\s*\(\s*\)\s*;",
            snippet,
        ):
            var = m.group(1)
            typ = m.group(2)
            consumes.append(("integral", var, typ, None, None, m.start()))

        # var = provider.ConsumeBool();
        for m in re.finditer(
            r"(?:auto|const\s+auto|bool)\s+([A-Za-z_]\w*)\s*=\s*provider\.ConsumeBool\s*\(\s*\)\s*;",
            snippet,
        ):
            var = m.group(1)
            consumes.append(("bool", var, "uint8_t", 0, 1, m.start()))

        consumes.sort(key=lambda x: x[-1])

        # Only keep early consumes up to min_size bytes
        out = bytearray()
        for kind, var, typ, mn, mx, _ in consumes:
            sz = self._type_size(typ if kind != "bool" else "uint8_t")
            if len(out) + sz > min_size:
                break
            cls = self._classify_var(code, var)
            if cls == "options":
                raw = 0
            elif cls == "mode":
                raw = 1
            elif cls == "ovector":
                if kind == "inrange" and mn is not None and mx is not None and mx >= mn:
                    rng = mx - mn + 1
                    raw = (rng - 1) if rng > 0 else 0
                else:
                    raw = (1 << (8 * sz)) - 1
            elif cls == "len":
                raw = 0
            else:
                # default: try to bias to 0 for safety
                raw = 0

            out += self._pack_le(raw, sz)

        if len(out) < min_size:
            out += b"\x00" * (min_size - len(out))

        return bytes(out[:min_size])

    def _gen_from_delim(self, code: str, min_size: int) -> Optional[bytes]:
        # Identify common pattern/subject split delimiters
        if ("memchr" in code or "find" in code or "strchr" in code) and ("'\\0'" in code or '"\\0"' in code or "\\0" in code):
            # pattern\0subject
            payload = b"a\x00a"
            if len(payload) < min_size:
                payload += b"a" * (min_size - len(payload))
            else:
                payload = payload[:min_size]
            return payload

        if ("memchr" in code or "find" in code or "getline" in code) and ("'\\n'" in code or '"\\n"' in code or "\\n" in code):
            payload = b"a\na"
            if len(payload) < min_size:
                payload += b"a" * (min_size - len(payload))
            else:
                payload = payload[:min_size]
            return payload

        return None