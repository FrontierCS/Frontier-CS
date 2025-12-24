class Solution:
    def solve(self, src_path: str) -> bytes:
        N = 1194
        params = ", ".join(f"a{i}" for i in range(1, N + 1))
        script = f"def foo({params})\nend\nfoo\n"
        return script.encode()
