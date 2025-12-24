class Solution:
    def solve(self, src_path: str) -> bytes:
        n = 512
        args = '0' + ',0' * (n - 1)
        ruby_code = f'def foo(*a); end\nfoo({args})\n'
        return ruby_code.encode('utf-8')
