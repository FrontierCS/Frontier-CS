from typing import Any


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Construct a minimal valid baseline JPEG image that should exercise MJPEG decoding.
        def make_minimal_jpeg() -> bytes:
            parts = []

            # SOI marker
            parts.append(b"\xFF\xD8")

            # DQT segment: single 8-bit quantization table (all ones)
            qtable = bytes([1] * 64)
            dqt_data = bytearray()
            dqt_data.append(0x00)  # Pq=0 (8-bit), Tq=0
            dqt_data.extend(qtable)
            dqt_len = 2 + len(dqt_data)
            parts.append(b"\xFF\xDB" + dqt_len.to_bytes(2, "big") + dqt_data)

            # SOF0 segment: baseline DCT, 8x8, 1 component (grayscale)
            height = 8
            width = 8
            sof_data = bytearray()
            sof_data.append(8)  # sample precision
            sof_data.extend(height.to_bytes(2, "big"))
            sof_data.extend(width.to_bytes(2, "big"))
            sof_data.append(1)  # number of components
            sof_data.append(1)  # Component ID = 1
            sof_data.append(0x11)  # H=1, V=1
            sof_data.append(0)  # quant table 0
            sof_len = 2 + len(sof_data)
            parts.append(b"\xFF\xC0" + sof_len.to_bytes(2, "big") + sof_data)

            # DHT segment: minimal DC and AC Huffman tables
            # DC table: one code of length 1 for category 0
            bits_dc = [0] * 16
            bits_dc[0] = 1  # one code of length 1
            hvals_dc = [0x00]  # category 0

            # AC table: one code of length 1 for EOB (0x00)
            bits_ac = [0] * 16
            bits_ac[0] = 1  # one code of length 1
            hvals_ac = [0x00]  # EOB

            dht_data = bytearray()
            # DC table (class 0, id 0)
            dht_data.append(0x00)
            dht_data.extend(bytes(bits_dc))
            dht_data.extend(bytes(hvals_dc))
            # AC table (class 1, id 0)
            dht_data.append(0x10)
            dht_data.extend(bytes(bits_ac))
            dht_data.extend(bytes(hvals_ac))

            dht_len = 2 + len(dht_data)
            parts.append(b"\xFF\xC4" + dht_len.to_bytes(2, "big") + dht_data)

            # SOS segment: single-component scan using DC table 0 and AC table 0
            sos_data = bytearray()
            sos_data.append(1)  # number of components in scan
            sos_data.append(1)  # component 1
            sos_data.append(0x00)  # DC table 0, AC table 0
            sos_data.append(0x00)  # Ss
            sos_data.append(0x3F)  # Se
            sos_data.append(0x00)  # Ah/Al
            sos_len = 2 + len(sos_data)
            parts.append(b"\xFF\xDA" + sos_len.to_bytes(2, "big") + sos_data)

            # Scan data:
            # DC diff = 0 => category 0 => code '0'
            # AC coefficients: EOB (0x00) => code '0'
            # Two bits '00' packed and padded => single byte 0x00.
            scan_data = b"\x00"
            parts.append(scan_data)

            # EOI marker
            parts.append(b"\xFF\xD9")

            return b"".join(parts)

        return make_minimal_jpeg()
