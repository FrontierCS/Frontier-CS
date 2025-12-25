import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def _read_tar_member_text(self, tar: tarfile.TarFile, member: tarfile.TarInfo, limit: int = 2_000_000) -> str:
        f = tar.extractfile(member)
        if not f:
            return ""
        data = f.read(limit + 1)
        if len(data) > limit:
            data = data[:limit]
        return data.decode("utf-8", "ignore")

    def _find_member_by_pred(self, tar: tarfile.TarFile, pred) -> Optional[tarfile.TarInfo]:
        for m in tar.getmembers():
            if not m.isfile():
                continue
            name = m.name
            try:
                if pred(name):
                    return m
            except Exception:
                continue
        return None

    def _find_all_members_by_pred(self, tar: tarfile.TarFile, pred) -> List[tarfile.TarInfo]:
        out = []
        for m in tar.getmembers():
            if not m.isfile():
                continue
            name = m.name
            try:
                if pred(name):
                    out.append(m)
            except Exception:
                continue
        return out

    def _parse_bsf_list(self, src: str) -> List[str]:
        m = re.search(r'\bbsfs\s*\[\s*\]\s*=\s*\{(.*?)\}\s*;', src, flags=re.S)
        if not m:
            m = re.search(r'\bbsfs\s*\[\s*\]\s*=\s*\{(.*?)\};', src, flags=re.S)
        if not m:
            m = re.search(r'\bconst\s+char\s*\*\s*(?:const\s*)?bsfs\s*\[\s*\]\s*=\s*\{(.*?)\}\s*;', src, flags=re.S)
        if not m:
            return []
        blob = m.group(1)
        items = re.findall(r'"([^"]+)"', blob)
        return items

    def _parse_fuzzer_info(self, src: str) -> Dict[str, object]:
        info: Dict[str, object] = {
            "selector_pos": 0,
            "selector_modulo": True,
            "prefix_len": 1,
            "min_total_size": 1,
            "string_mode": False,
        }

        # minimum input size check
        mins = []
        for mm in re.finditer(r'\bif\s*\(\s*size\s*<\s*(\d+)\s*\)\s*return\b', src):
            try:
                mins.append(int(mm.group(1)))
            except Exception:
                pass
        if mins:
            info["min_total_size"] = max(mins)

        # packet prefix length
        mm = re.search(r'\bpkt\s*\.\s*data\s*=\s*(?:\(\s*uint8_t\s*\*\s*\)\s*)?data\s*\+\s*(\d+)\s*;', src)
        if mm:
            info["prefix_len"] = int(mm.group(1))
        else:
            mm = re.search(r'\bpkt\s*\.\s*data\s*=\s*(?:\(\s*uint8_t\s*\*\s*\)\s*)?data\s*;', src)
            if mm:
                info["prefix_len"] = 0

        # selection position / modulo
        mm = re.search(r'bsfs\s*\[\s*data\s*\[\s*(\d+)\s*\]\s*%\s*FF_ARRAY_ELEMS\s*\(\s*bsfs\s*\)\s*\]', src)
        if mm:
            info["selector_pos"] = int(mm.group(1))
            info["selector_modulo"] = True
        else:
            mm = re.search(r'bsfs\s*\[\s*data\s*\[\s*(\d+)\s*\]\s*\]', src)
            if mm:
                info["selector_pos"] = int(mm.group(1))
                info["selector_modulo"] = False

        # string mode
        if "av_bsf_get_by_name" in src and "bsfs[" not in src:
            info["string_mode"] = True

        # Make sure prefix_len at least covers selector if selector is a raw byte before pkt.data
        try:
            sel_pos = int(info["selector_pos"])
            pref = int(info["prefix_len"])
            if pref <= sel_pos:
                info["prefix_len"] = sel_pos + 1
        except Exception:
            pass

        return info

    def _infer_filter_requirements(self, src: str) -> Dict[str, object]:
        req: Dict[str, object] = {
            "jpeg_offset": 0,
            "min_packet_size": 128,
            "exact_packet_size": None,
            "required_bytes": {},  # offset -> value
        }

        # Detect required byte comparisons near early returns
        required_bytes: Dict[int, int] = {}
        for m in re.finditer(r'(if\s*\(.*?\)\s*return\b.*?;)', src, flags=re.S):
            block = m.group(1)
            for bm in re.finditer(r'(?:pkt|in)\s*->\s*data\s*\[\s*(\d+)\s*\]\s*!=\s*(0x[0-9a-fA-F]+|\d+)', block):
                off = int(bm.group(1))
                val_s = bm.group(2)
                val = int(val_s, 0)
                if 0 <= off < 4096 and 0 <= val < 256:
                    required_bytes[off] = val

        # Detect MKTAG equality requirements with AV_RL32(... ) != MKTAG(...)
        for mm in re.finditer(r'AV_RL32\s*\(\s*([^)]+?)\s*\)\s*!=\s*MKTAG\s*\(\s*\'(.?)\'\s*,\s*\'(.?)\'\s*,\s*\'(.?)\'\s*,\s*\'(.?)\'\s*\)', src):
            expr = mm.group(1)
            if "return" not in src[mm.start():mm.start() + 200]:
                continue
            offm = re.search(r'\+\s*(\d+)', expr)
            off = int(offm.group(1)) if offm else 0
            a, b, c, d = mm.group(2), mm.group(3), mm.group(4), mm.group(5)
            tag = bytes([ord(a), ord(b), ord(c), ord(d)])
            if 0 <= off < 4096:
                required_bytes[off + 0] = tag[0]
                required_bytes[off + 1] = tag[1]
                required_bytes[off + 2] = tag[2]
                required_bytes[off + 3] = tag[3]

        req["required_bytes"] = required_bytes

        # Infer jpeg offset from explicit 0xffd8 checks
        offsets = []
        for mm in re.finditer(r'AV_RB16\s*\(\s*[^)]*?\+\s*(\d+)\s*\)\s*!=\s*0x?ff?d8', src, flags=re.I):
            offsets.append(int(mm.group(1)))
        for mm in re.finditer(r'AV_RB16\s*\(\s*[^)]*?\+\s*(\d+)\s*\)\s*==\s*0x?ff?d8', src, flags=re.I):
            offsets.append(int(mm.group(1)))
        if offsets:
            req["jpeg_offset"] = min(offsets)

        # If required bytes exist at offset 0..3 and jpeg_offset is 0, move jpeg_offset to 4 as a common header size.
        if req["jpeg_offset"] == 0:
            for k in required_bytes.keys():
                if 0 <= k <= 3:
                    req["jpeg_offset"] = 4
                    break

        # Infer packet size requirements
        min_sizes = []
        exact_sizes = []

        for mm in re.finditer(r'(?:pkt|in)\s*->\s*size\s*<\s*(\d+)', src):
            val = int(mm.group(1))
            if 0 < val <= 1_000_000:
                min_sizes.append(val)

        # exact size if line contains return and '!= N'
        for line in src.splitlines():
            if "->size" in line and "!=" in line and "return" in line:
                mm = re.search(r'->\s*size\s*!=\s*(\d+)', line)
                if mm:
                    val = int(mm.group(1))
                    if 0 < val <= 1_000_000:
                        exact_sizes.append(val)

        if min_sizes:
            req["min_packet_size"] = max(req["min_packet_size"], max(min_sizes))
        if exact_sizes:
            # choose the largest exact size, typically one
            req["exact_packet_size"] = max(exact_sizes)
            req["min_packet_size"] = max(req["min_packet_size"], req["exact_packet_size"])

        # Common alignment/sector sizes present in some formats
        if req["min_packet_size"] < 1024 and re.search(r'\b1024\b', src) and "size < 1024" in src:
            req["min_packet_size"] = max(req["min_packet_size"], 1024)

        return req

    def _build_minimal_jpeg_payload(self, total_size: int, jpeg_offset: int, required_bytes: Dict[int, int]) -> bytes:
        # JPEG without DHT segments: SOI + DQT + SOF0 + SOS + scan_data + EOI
        soi = b"\xFF\xD8"
        dqt_vals = bytes([1] * 64)
        dqt = b"\xFF\xDB\x00\x43\x00" + dqt_vals  # marker + length + info + 64 bytes
        # SOF0 for 16x16, 3 components
        height = 16
        width = 16
        sof0 = bytearray()
        sof0 += b"\xFF\xC0\x00\x11"
        sof0 += b"\x08"
        sof0 += bytes([(height >> 8) & 0xFF, height & 0xFF, (width >> 8) & 0xFF, width & 0xFF])
        sof0 += b"\x03"
        sof0 += b"\x01\x22\x00"
        sof0 += b"\x02\x11\x00"
        sof0 += b"\x03\x11\x00"
        sof0 = bytes(sof0)
        # SOS with 3 components, huffman table selectors 0
        sos = bytearray()
        sos += b"\xFF\xDA\x00\x0C"
        sos += b"\x03"
        sos += b"\x01\x00"
        sos += b"\x02\x00"
        sos += b"\x03\x00"
        sos += b"\x00\x3F\x00"
        sos = bytes(sos)

        header = soi + dqt + sof0 + sos
        if total_size < jpeg_offset + len(header) + 2 + 1:
            total_size = jpeg_offset + len(header) + 2 + 1

        buf = bytearray(b"\x00" * total_size)
        for off, val in required_bytes.items():
            if 0 <= off < total_size:
                buf[off] = val & 0xFF

        # If required bytes overlap jpeg start marker, prefer required bytes by shifting jpeg_offset if possible
        if jpeg_offset + 1 < total_size:
            if jpeg_offset in required_bytes and required_bytes[jpeg_offset] != 0xFF:
                jpeg_offset = min(jpeg_offset + 4, total_size - 2)
            if jpeg_offset + 1 in required_bytes and required_bytes[jpeg_offset + 1] != 0xD8:
                jpeg_offset = min(jpeg_offset + 4, total_size - 2)

        scan_len = total_size - jpeg_offset - len(header) - 2
        if scan_len < 1:
            scan_len = 1
            total_size = jpeg_offset + len(header) + scan_len + 2
            buf = bytearray(b"\x00" * total_size)
            for off, val in required_bytes.items():
                if 0 <= off < total_size:
                    buf[off] = val & 0xFF

        buf[jpeg_offset:jpeg_offset + len(header)] = header
        # scan data: all zeros (no 0xFF to avoid accidental marker parsing)
        scan_start = jpeg_offset + len(header)
        buf[scan_start:scan_start + scan_len] = b"\x00" * scan_len
        buf[-2:] = b"\xFF\xD9"
        return bytes(buf)

    def solve(self, src_path: str) -> bytes:
        target_bsf = "media100_to_mjpegb"

        with tarfile.open(src_path, "r:*") as tar:
            # Find filter source file
            bsf_member = self._find_member_by_pred(
                tar,
                lambda n: n.endswith("/" + target_bsf + ".c") or os.path.basename(n) == (target_bsf + ".c") or (target_bsf in n and n.endswith(".c")),
            )
            bsf_src = self._read_tar_member_text(tar, bsf_member) if bsf_member else ""

            # Find a bsf fuzzer harness containing the target name if possible
            cand_members = self._find_all_members_by_pred(
                tar,
                lambda n: (n.endswith(".c") or n.endswith(".cc") or n.endswith(".cpp")) and ("fuzz" in n.lower() or "fuzzer" in n.lower() or "oss-fuzz" in n.lower()),
            )
            fuzzer_src = ""
            for m in cand_members:
                s = self._read_tar_member_text(tar, m, limit=1_000_000)
                if "LLVMFuzzerTestOneInput" not in s:
                    continue
                if target_bsf in s and "av_bsf" in s:
                    fuzzer_src = s
                    break
            if not fuzzer_src:
                for m in cand_members:
                    s = self._read_tar_member_text(tar, m, limit=600_000)
                    if "LLVMFuzzerTestOneInput" in s and "av_bsf" in s and "bsf" in s.lower():
                        fuzzer_src = s
                        break

        filter_req = self._infer_filter_requirements(bsf_src) if bsf_src else {
            "jpeg_offset": 0,
            "min_packet_size": 1024,
            "exact_packet_size": None,
            "required_bytes": {},
        }

        fuzzer_info = self._parse_fuzzer_info(fuzzer_src) if fuzzer_src else {
            "selector_pos": 0,
            "selector_modulo": True,
            "prefix_len": 1,
            "min_total_size": 1,
            "string_mode": False,
        }

        bsf_list = self._parse_bsf_list(fuzzer_src) if fuzzer_src else []
        selector_pos = int(fuzzer_info.get("selector_pos", 0))
        prefix_len = int(fuzzer_info.get("prefix_len", 1))
        min_total = int(fuzzer_info.get("min_total_size", 1))
        string_mode = bool(fuzzer_info.get("string_mode", False))
        selector_mod = bool(fuzzer_info.get("selector_modulo", True))

        # Determine packet size requirements
        packet_size = int(filter_req.get("min_packet_size", 1024))
        exact_ps = filter_req.get("exact_packet_size", None)
        if isinstance(exact_ps, int) and exact_ps > 0:
            packet_size = exact_ps

        jpeg_offset = int(filter_req.get("jpeg_offset", 0))
        required_bytes = filter_req.get("required_bytes", {}) or {}
        if not isinstance(required_bytes, dict):
            required_bytes = {}

        packet = self._build_minimal_jpeg_payload(packet_size, jpeg_offset, required_bytes)

        if string_mode and not bsf_list:
            name = (target_bsf + "\x00").encode("ascii", "strict")
            out = name + packet
            if len(out) < min_total:
                out = out + b"\x00" * (min_total - len(out))
            return out

        if bsf_list:
            try:
                idx = bsf_list.index(target_bsf)
            except ValueError:
                idx = 0
        else:
            idx = 0

        # Build prefix bytes
        total_size = max(min_total, prefix_len + len(packet))
        out = bytearray(b"\x00" * total_size)

        # Put packet
        out[prefix_len:prefix_len + len(packet)] = packet

        # Set selector byte
        if bsf_list:
            n = len(bsf_list)
            if n <= 0:
                sel_val = 0
            else:
                if selector_mod:
                    sel_val = idx % n
                else:
                    sel_val = idx
                sel_val &= 0xFF
            if 0 <= selector_pos < len(out):
                out[selector_pos] = sel_val

        return bytes(out)